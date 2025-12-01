import os
import asyncio
import random
import time
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Tuple, Optional
import threading

app = FastAPI()

# --- Configuration ---
ROLE = os.getenv("ROLE", "follower")
PORT = int(os.getenv("PORT", "5000"))
FOLLOWERS_LIST = os.getenv("FOLLOWERS", "").split(",") if os.getenv("FOLLOWERS") else []
MIN_DELAY = float(os.getenv("MIN_DELAY", "0"))
MAX_DELAY = float(os.getenv("MAX_DELAY", "1"))
current_write_quorum = int(os.getenv("WRITE_QUORUM", "1"))

# --- Storage ---
store: Dict[str, Tuple[str, float, int]] = {}

# --- Locks ---
store_lock = asyncio.Lock()
config_lock = asyncio.Lock()

# Sequence counter - using threading.Lock for true thread-safety
_sequence_counter = 0
_sequence_lock = threading.Lock()


def get_next_sequence() -> int:
    """Thread-safe sequence number generator"""
    global _sequence_counter
    with _sequence_lock:
        _sequence_counter += 1
        return _sequence_counter


# --- Models ---


class WriteRequest(BaseModel):
    key: str
    value: str
    timestamp: Optional[float] = None
    sequence: Optional[int] = None


class ConfigRequest(BaseModel):
    quorum: int


# --- HTTP Client ---
client = httpx.AsyncClient()


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()


# --- Endpoints ---


@app.get("/health")
async def health():
    return {"status": "ok", "role": ROLE}


@app.get("/read/{key}")
async def read_key(key: str):
    async with store_lock:
        if key in store:
            value, timestamp, sequence = store[key]
            return {
                "key": key,
                "value": value,
                "timestamp": timestamp,
                "sequence": sequence,
            }
    raise HTTPException(status_code=404, detail="Key not found")


@app.get("/read_all")
async def read_all():
    async with store_lock:
        return {key: value for key, (value, _, _) in store.items()}


@app.delete("/clear")
async def clear_store():
    async with store_lock:
        store.clear()
    return {"status": "cleared", "role": ROLE}


# --- Follower Logic ---
if ROLE == "follower":

    @app.post("/replication")
    async def replicate(data: WriteRequest):
        async with store_lock:
            should_apply = False

            if data.key in store:
                current_value, current_timestamp, current_sequence = store[data.key]
                # Compare based on sequence first (primary), then timestamp as fallback (secondary)
                # This ensures consistent ordering of updates
                if data.sequence is not None and current_sequence is not None:
                    # Use sequence number as primary ordering mechanism
                    should_apply = data.sequence > current_sequence
                elif data.timestamp is not None and current_timestamp is not None:
                    # Use timestamp as secondary ordering mechanism when sequences are not available
                    should_apply = data.timestamp > current_timestamp
                else:
                    # If both are None, apply the data
                    should_apply = True
            else:
                should_apply = True

            if should_apply:
                store[data.key] = (data.value, data.timestamp, data.sequence)
                return {"status": "ack", "applied": True}
            else:
                return {"status": "ack", "applied": False, "reason": "stale_write"}


# --- Leader Logic ---
if ROLE == "leader":

    @app.post("/config")
    async def update_config(cfg: ConfigRequest):
        global current_write_quorum
        async with config_lock:
            current_write_quorum = cfg.quorum
            return {"status": "updated", "quorum": current_write_quorum}

    async def send_replication(follower_url: str, data: WriteRequest):
        try:
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            await asyncio.sleep(delay)

            resp = await client.post(
                f"{follower_url}/replication", json=data.model_dump(), timeout=10.0
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Failed to replicate to {follower_url}: {e}")
            return False

    @app.post("/write")
    async def write_key(data: WriteRequest):
        # CRITICAL: Assign sequence number IMMEDIATELY at entry
        # This ensures sequence reflects arrival order
        if data.sequence is None:
            data.sequence = get_next_sequence()

        if data.timestamp is None:
            data.timestamp = time.time()

        final_sequence = data.sequence
        final_timestamp = data.timestamp

        # Always replicate to followers regardless of whether we write locally
        # This ensures followers get all updates that clients send to leader
        should_replicate = True

        # Write locally - only if sequence is newer
        async with store_lock:
            should_write = True

            if data.key in store:
                _, existing_timestamp, existing_sequence = store[data.key]
                # Only write if our sequence is strictly greater
                if (
                    existing_sequence is not None
                    and final_sequence <= existing_sequence
                ):
                    should_write = False

            if should_write:
                store[data.key] = (data.value, final_timestamp, final_sequence)

        # Replicate to followers if needed
        if not should_replicate or not FOLLOWERS_LIST or FOLLOWERS_LIST == [""]:
            return {"status": "success"}

        async with config_lock:
            required_acks = current_write_quorum

        tasks = [send_replication(url, data) for url in FOLLOWERS_LIST]
        needed_remote_acks = max(0, required_acks)

        if needed_remote_acks == 0:
            asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))
            return {"status": "success"}

        finished_acks = 0

        for coro in asyncio.as_completed(tasks):
            try:
                success = await coro
                if success:
                    finished_acks += 1

                if finished_acks >= needed_remote_acks:
                    break
            except Exception as e:
                print(f"Replication error: {e}")

        if finished_acks >= needed_remote_acks:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Write quorum not met")


# --- Entry Point ---
if __name__ == "__main__":
    import uvicorn

    print(f"Starting {ROLE} on port {PORT}")
    print(f"Write quorum: {current_write_quorum if ROLE == 'leader' else 'N/A'}")
    print(f"Followers: {FOLLOWERS_LIST if ROLE == 'leader' else 'N/A'}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

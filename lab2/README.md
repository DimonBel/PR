# Lab 2: Concurrent HTTP Server

This folder contains a multithreaded HTTP server implementation and benchmarking utilities for Lab 2.

## Files

- `server_threaded.py`: Thread-pooled HTTP server with:
  - Artificial per-request delay (default 1s)
  - Per-file request counter (naive or locked)
  - Per-IP rate limiting (~5 req/s by default)
  - Directory listing that shows per-file request counts
- `client_bench.py`: Benchmarking client to test concurrency and rate limiting.

## Running the server

```bash
# From the project root or lab2 directory
python3 lab2/server_threaded.py
```

Environment variables to configure behavior:

- `PORT` (default `8080`): Server port
- `HOST` (default `0.0.0.0`)
- `WORKERS` (default `32`): Thread pool size
- `DOC_ROOT` (default current working directory when server starts)
- `DELAY` (default `1.0`): Artificial per-request delay in seconds
- `COUNTER_MODE` (default `locked`): `naive` or `locked`
- `RATE_LIMIT` (default `5`): Max requests per second per IP
- `RATE_WINDOW` (default `1.0`): Window size in seconds

Examples:

```bash
# Serve current project root with 1s delay, locked counters, and default rate limit
PORT=8080 WORKERS=32 DELAY=1.0 COUNTER_MODE=locked python3 lab2/server_threaded.py

# Demonstrate race condition in naive counter
COUNTER_MODE=naive python3 lab2/server_threaded.py
```

## Benchmark: Concurrency

Run the benchmarking client to issue N concurrent requests and measure total time:

```bash
# Issue 10 concurrent requests to root
python3 lab2/client_bench.py --url http://localhost:8080/ --concurrent 10 --mode concurrency
```

Expected timing:
- Single-threaded baseline (from Lab 1) with 1s delay: ~10s for 10 requests.
- Multithreaded (workers >= 10): ~1–2s for 10 requests.

## Benchmark: Rate limiting

Test with a single client sending at a specified rate (req/s):

```bash
# Send at 10 req/s for 5s and observe 429s around the 5 req/s limit
python3 lab2/client_bench.py --url http://localhost:8080/ --mode rate --rate 10 --rate-duration 5

# Send below the limit (e.g., 4 req/s) and expect near 100% success
python3 lab2/client_bench.py --url http://localhost:8080/ --mode rate --rate 4 --rate-duration 5
```

For a two-client test (simulating two IPs), run the rate test from two different machines or containers so they have different source IPs. Otherwise, results are per the same IP and will share the limit.

## Directory listing with counts

The server shows per-file request counts next to files in directory listings. Counts are keyed by the file path relative to the document root.

## Notes

- This server is a simple educational implementation (HTTP/1.1 without keep-alive or chunked encoding). It is suitable for local testing and learning, not for production.
- The rate limiter uses a sliding window per IP with a shared lock for simplicity.
- The naive counter intentionally introduces a race to demonstrate incorrect results under concurrency; use `COUNTER_MODE=locked` for the correct solution.

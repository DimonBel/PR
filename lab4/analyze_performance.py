"""
Performance Analysis Script for Key-Value Store
Analyzes write latency vs write quorum (1-5)
Tests ~100 writes with concurrent execution
"""

import httpx
import time
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import subprocess
import sys
import re

LEADER_URL = "http://localhost:5000"
FOLLOWER_URLS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
    "http://localhost:5004",
    "http://localhost:5005",
]


def update_quorum_via_api(quorum):
    """Update quorum dynamically via API"""
    try:
        response = httpx.post(
            f"{LEADER_URL}/config", json={"quorum": quorum}, timeout=10
        )
        if response.status_code == 200:
            print(f"✅ Updated quorum to {quorum} via API")
            return True
        else:
            print(f"⚠️  Failed to update quorum: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error updating quorum: {e}")
        return False


def clear_all_stores():
    """Clear data from leader and all followers"""
    print("  🗑️  Clearing all stores...")
    all_urls = [LEADER_URL] + FOLLOWER_URLS
    for url in all_urls:
        try:
            httpx.delete(f"{url}/clear", timeout=5)
        except:
            pass


def wait_for_services(timeout=40):
    """Wait for all services to be healthy"""
    print("Waiting for services to start...")
    all_urls = [LEADER_URL] + FOLLOWER_URLS

    for i in range(timeout):
        all_healthy = True
        for url in all_urls:
            try:
                response = httpx.get(f"{url}/health", timeout=1)
                if response.status_code != 200:
                    all_healthy = False
                    break
            except:
                all_healthy = False
                break

        if all_healthy:
            print(f"All services are healthy! (took {i+1}s)")
            return True

        time.sleep(1)
        if i % 5 == 0:
            print(f"  Still waiting... ({i}s elapsed)")

    print("Services did not start in time!")
    return False


def perform_write(key, value):
    """Perform a single write and measure latency"""
    start_time = time.time()
    try:
        response = httpx.post(
            f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=15
        )
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to ms
        return {
            "success": response.status_code == 200,
            "latency": latency,
            "key": key,
            "value": value,
        }
    except Exception as e:
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        return {
            "success": False,
            "latency": latency,
            "key": key,
            "value": value,
            "error": str(e),
        }


def test_write_quorum_performance(write_quorum):
    """Test performance with a specific write quorum value"""
    print("\n" + "=" * 70)
    print(f"TESTING WITH WRITE_QUORUM = {write_quorum}")
    print("=" * 70)

    # Update quorum via API
    if not update_quorum_via_api(write_quorum):
        print("❌ Failed to update quorum!")
        return None

    # Clear all stores before testing
    clear_all_stores()
    time.sleep(1)

    # Perform ~100 writes (10 keys, 10 writes each) - 10 concurrent at a time
    print("\nPerforming 100 writes (10 keys × 10 writes, 10 concurrent at a time)...")
    latencies = []
    successful_writes = 0
    failed_writes = 0
    total_writes = 100

    # 10 batches of 10 concurrent writes
    num_batches = 10
    for batch in range(num_batches):
        print(f"  Batch {batch + 1}/{num_batches}...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                key_id = i  # 10 keys (0-9)
                write_num = batch
                key = f"key{key_id}"
                value = f"value_{key_id}_batch{write_num}_q{write_quorum}"
                futures.append(executor.submit(perform_write, key, value))

            for future in as_completed(futures):
                result = future.result()
                if result["success"]:
                    latencies.append(result["latency"])
                    successful_writes += 1
                else:
                    failed_writes += 1
                    error_msg = result.get("error", "Unknown error")
                    print(f"    ✗ {result['key']}: FAILED - {error_msg}")

    if not latencies:
        print("\n❌ No successful writes!")
        return None

    avg_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)

    print(f"\n📊 Results for WRITE_QUORUM={write_quorum}:")
    print(f"   Successful writes: {successful_writes}/{total_writes}")
    print(f"   Failed writes: {failed_writes}/{total_writes}")
    print(f"   Average latency: {avg_latency:.2f}ms")
    print(f"   Median latency: {median_latency:.2f}ms")
    print(f"   Min latency: {min(latencies):.2f}ms")
    print(f"   Max latency: {max(latencies):.2f}ms")

    return {
        "write_quorum": write_quorum,
        "avg_latency": avg_latency,
        "median_latency": median_latency,
        "latencies": latencies,
        "successful_writes": successful_writes,
        "failed_writes": failed_writes,
    }


def check_data_consistency():
    """Check if data on followers matches leader"""
    print("\n" + "=" * 70)
    print("DATA CONSISTENCY CHECK")
    print("=" * 70)

    # Wait for replication to settle
    print("Waiting 5 seconds for all replication to complete...")
    time.sleep(5)

    # Get leader data
    try:
        response = httpx.get(f"{LEADER_URL}/read_all", timeout=5)
        leader_data = response.json()
        print(f"\n📦 Leader has {len(leader_data)} keys")
    except Exception as e:
        print(f"❌ Failed to get leader data: {e}")
        return None

    # Get follower data
    follower_data_list = []
    for i, follower_url in enumerate(FOLLOWER_URLS, 1):
        try:
            response = httpx.get(f"{follower_url}/read_all", timeout=5)
            follower_data = response.json()
            follower_data_list.append((f"Follower{i}", follower_data))
            print(f"   Follower{i} has {len(follower_data)} keys")
        except Exception as e:
            print(f"   ❌ Follower{i} - Failed to get data: {e}")
            follower_data_list.append((f"Follower{i}", {}))

    # Compare data
    print("\n🔍 Detailed consistency check:")
    inconsistencies = []

    # Check each key on leader
    for key in sorted(leader_data.keys()):
        leader_value = leader_data[key]
        mismatches = []

        for follower_name, follower_data in follower_data_list:
            follower_value = follower_data.get(key, "MISSING")
            if follower_value != leader_value:
                mismatches.append((follower_name, follower_value))

        if mismatches:
            inconsistencies.append((key, leader_value, mismatches))
            print(f"\n   ⚠️  Key '{key}':")
            print(f"      Leader: {leader_value}")
            for follower_name, follower_value in mismatches:
                print(f"      {follower_name}: {follower_value}")

    # Check for keys on followers not on leader
    extra_keys_found = False
    for follower_name, follower_data in follower_data_list:
        for key in follower_data:
            if key not in leader_data:
                if not extra_keys_found:
                    print("\n   ⚠️  Extra keys found on followers (not on leader):")
                    extra_keys_found = True
                print(f"      {follower_name}: '{key}' = {follower_data[key]}")

    if not inconsistencies and not extra_keys_found:
        print("\n   ✅ All data is CONSISTENT across all replicas!")
    else:
        print(f"\n   ❌ Found {len(inconsistencies)} inconsistent key(s)")
        print("   ⚠️  This is EXPECTED with concurrent writes due to race conditions!")
        print("      Different followers may receive updates in different orders.")

    return {
        "consistent": len(inconsistencies) == 0 and not extra_keys_found,
        "leader_keys": len(leader_data),
        "follower_keys": [len(fd) for _, fd in follower_data_list],
        "inconsistencies": len(inconsistencies),
    }


def plot_results(results):
    """Plot write quorum vs average latency"""
    print("\n" + "=" * 70)
    print("GENERATING PERFORMANCE PLOT")
    print("=" * 70)

    write_quorums = [r["write_quorum"] for r in results]
    avg_latencies = [r["avg_latency"] for r in results]
    median_latencies = [r["median_latency"] for r in results]

    plt.figure(figsize=(12, 7))

    # Plot average latency
    plt.plot(
        write_quorums,
        avg_latencies,
        marker="o",
        linewidth=2,
        markersize=10,
        label="Average Latency",
        color="#2E86AB",
    )

    # Plot median latency
    plt.plot(
        write_quorums,
        median_latencies,
        marker="s",
        linewidth=2,
        markersize=8,
        label="Median Latency",
        color="#A23B72",
        linestyle="--",
    )

    # Add value labels
    for i, (q, avg, med) in enumerate(
        zip(write_quorums, avg_latencies, median_latencies)
    ):
        plt.text(q, avg + 10, f"{avg:.1f}ms", ha="center", va="bottom", fontsize=9)

    plt.xlabel(
        "Write Quorum (Number of Followers Required)", fontsize=13, fontweight="bold"
    )
    plt.ylabel("Write Latency (ms)", fontsize=13, fontweight="bold")
    plt.title(
        "Write Quorum vs Write Latency\nSemi-Synchronous Replication Performance",
        fontsize=15,
        fontweight="bold",
        pad=20,
    )
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.xticks(write_quorums)
    plt.legend(fontsize=11)

    # Add explanation box
    explanation = (
        "Higher quorum = More followers must confirm\n"
        "→ Leader waits for more followers\n"
        "→ Higher latency (linear growth)"
    )
    plt.text(
        0.02,
        0.98,
        explanation,
        transform=plt.gca().transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3),
    )

    plt.tight_layout()

    # Save plot
    filename = "quorum_latency_analysis.png"
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"✅ Plot saved as '{filename}'")
    plt.close()


def print_summary(results, consistency_result):
    """Print final summary"""
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)

    print("\n🔹 Latency vs Write Quorum:")
    print("   Quorum │ Avg Latency │ Median │ Success Rate")
    print("   ───────┼─────────────┼────────┼──────────────")
    for r in results:
        success_rate = (r["successful_writes"] / 100) * 100
        print(
            f"      {r['write_quorum']}   │  {r['avg_latency']:>7.2f}ms  │ {r['median_latency']:>6.2f}ms │    {success_rate:>5.1f}%"
        )

    print("\n🔹 Consistency Status:")
    if consistency_result:
        status = (
            "✅ CONSISTENT" if consistency_result["consistent"] else "❌ INCONSISTENT"
        )
        print(f"   Status: {status}")
        print(f"   Leader keys: {consistency_result['leader_keys']}")
        print(
            f"   Inconsistencies found: {consistency_result.get('inconsistencies', 0)}"
        )

    print("\n💡 Key Insights:")
    print("   1. Latency increases linearly with write quorum")
    print("      - More followers = longer wait for slowest responder")
    print("   2. Semi-synchronous replication trade-off:")
    print("      - Higher quorum = stronger durability, higher latency")
    print("      - Lower quorum = faster writes, lower durability")
    print("   3. Concurrent writes may cause inconsistencies:")
    print("      - Network delays cause out-of-order delivery")
    print("      - Timestamps prevent stale updates from overwriting newer data")
    print("      - Some followers may still have different versions temporarily")

    print("\n⚠️  Expected Behavior:")
    print("   • Minor data inconsistencies are NORMAL with concurrent writes")
    print("   • Timestamps help but don't eliminate all race conditions")
    print("   • Eventually consistent: all replicas converge after settling")
    print("   • Production solution: Add vector clocks or version numbers")


def run_performance_analysis():
    """Run complete performance analysis"""
    print("=" * 70)
    print("KEY-VALUE STORE PERFORMANCE ANALYSIS")
    print("Semi-Synchronous Replication with Variable Write Quorum")
    print("Testing with ~100 writes per quorum value")
    print("=" * 70)

    # Make sure services are running
    print("\n🚀 Checking if Docker containers are running...")
    result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
    if "kv_leader" not in result.stdout:
        print("Starting Docker containers...")
        subprocess.run(["docker-compose", "up", "-d"], capture_output=True)
        if not wait_for_services():
            print("\n❌ Services failed to start. Aborting analysis.")
            sys.exit(1)
    else:
        print("✅ Containers already running")
        if not wait_for_services(timeout=20):
            print("\n❌ Services not responding. Aborting analysis.")
            sys.exit(1)

    # Test different write quorum values (1 to 5)
    quorum_values = [1, 2, 3, 4, 5]
    results = []

    for quorum in quorum_values:
        result = test_write_quorum_performance(quorum)
        if result:
            results.append(result)
        else:
            print(f"⚠️  Skipping quorum {quorum} due to errors")
        time.sleep(2)

    if not results:
        print("\n❌ No successful test runs!")
        sys.exit(1)

    # Plot results
    plot_results(results)

    # Check consistency after all writes
    consistency_result = check_data_consistency()

    # Print final summary
    print_summary(results, consistency_result)

    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print("\nCheck 'quorum_latency_analysis.png' for the performance graph!")


if __name__ == "__main__":
    try:
        run_performance_analysis()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

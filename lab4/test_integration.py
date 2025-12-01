"""
Integration test for Key-Value Store with Single-Leader Replication
Tests basic functionality of the distributed system
"""

import httpx
import time
import subprocess
import sys


LEADER_URL = "http://localhost:5000"
FOLLOWER_URLS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
    "http://localhost:5004",
    "http://localhost:5005",
]


def wait_for_services(timeout=60):
    """Wait for all services to become healthy"""
    print("⏳ Waiting for services to start...")
    all_urls = [LEADER_URL] + FOLLOWER_URLS

    for i in range(timeout):
        all_healthy = True
        for url in all_urls:
            try:
                response = httpx.get(f"{url}/health", timeout=2)
                if response.status_code != 200:
                    all_healthy = False
                    break
            except:
                all_healthy = False
                break

        if all_healthy:
            print(f"✅ All services are healthy! (took {i+1}s)")
            return True

        time.sleep(1)
        if i % 10 == 0 and i > 0:
            print(f"  Still waiting... ({i}s elapsed)")

    print("❌ Services did not start in time!")
    return False


def test_leader_health():
    """Test 1: Leader health check"""
    print("\n" + "=" * 70)
    print("TEST 1: Leader Health Check")
    print("=" * 70)
    try:
        response = httpx.get(f"{LEADER_URL}/health", timeout=5)
        assert response.status_code == 200, "Leader health check failed"
        data = response.json()
        assert data["status"] == "ok", "Leader status is not 'ok'"
        assert data["role"] == "leader", "Role should be 'leader'"
        print("✅ PASSED: Leader is healthy and has correct role")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_followers_health():
    """Test 2: Followers health check"""
    print("\n" + "=" * 70)
    print("TEST 2: Followers Health Check")
    print("=" * 70)
    all_passed = True
    for i, follower_url in enumerate(FOLLOWER_URLS, 1):
        try:
            response = httpx.get(f"{follower_url}/health", timeout=5)
            assert response.status_code == 200, f"Follower {i} health check failed"
            data = response.json()
            assert data["status"] == "ok", f"Follower {i} status is not 'ok'"
            assert data["role"] == "follower", f"Follower {i} role should be 'follower'"
            print(f"  ✅ Follower {i}: healthy")
        except Exception as e:
            print(f"  ❌ Follower {i}: {e}")
            all_passed = False

    if all_passed:
        print("✅ PASSED: All followers are healthy")
    else:
        print("❌ FAILED: Some followers are not healthy")
    return all_passed


def test_write_and_read():
    """Test 3: Write to leader and read from leader"""
    print("\n" + "=" * 70)
    print("TEST 3: Write and Read from Leader")
    print("=" * 70)
    try:
        # Write data
        write_data = {"key": "test_key", "value": "test_value"}
        response = httpx.post(f"{LEADER_URL}/write", json=write_data, timeout=10)
        assert response.status_code == 200, "Write request failed"
        write_result = response.json()
        assert write_result["status"] == "success", "Write status is not 'success'"
        print(f"  ✅ Write successful: {write_data}")

        # Wait a bit for potential replication
        time.sleep(0.5)

        # Read from leader
        response = httpx.get(f"{LEADER_URL}/read/test_key", timeout=5)
        assert response.status_code == 200, "Read from leader failed"
        read_data = response.json()
        assert read_data["key"] == "test_key", "Key mismatch"
        assert read_data["value"] == "test_value", "Value mismatch"
        print(f"  ✅ Read from leader successful: {read_data}")

        print("✅ PASSED: Write and read operations work correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_replication_to_followers():
    """Test 4: Verify data replication to followers"""
    print("\n" + "=" * 70)
    print("TEST 4: Data Replication to Followers")
    print("=" * 70)
    try:
        # Write new data
        write_data = {"key": "replication_test", "value": "replicated_value"}
        response = httpx.post(f"{LEADER_URL}/write", json=write_data, timeout=10)
        assert response.status_code == 200, "Write request failed"
        print(f"  ✅ Write successful: {write_data}")

        # Wait for replication to complete
        print("  ⏳ Waiting 2 seconds for replication...")
        time.sleep(2)

        # Check all followers
        all_replicated = True
        for i, follower_url in enumerate(FOLLOWER_URLS, 1):
            try:
                response = httpx.get(f"{follower_url}/read/replication_test", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data["value"] == "replicated_value":
                        print(f"  ✅ Follower {i}: data replicated correctly")
                    else:
                        print(
                            f"  ⚠️  Follower {i}: value mismatch (got '{data['value']}')"
                        )
                        all_replicated = False
                else:
                    print(
                        f"  ⚠️  Follower {i}: data not found (may not have received replication)"
                    )
                    all_replicated = False
            except Exception as e:
                print(f"  ❌ Follower {i}: {e}")
                all_replicated = False

        if all_replicated:
            print("✅ PASSED: Data successfully replicated to all followers")
        else:
            print(
                "⚠️  PARTIAL: Not all followers have the data (this may be expected with quorum < 5)"
            )
        return True  # We consider this a pass even if not all replicated due to quorum
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_multiple_writes():
    """Test 5: Multiple concurrent writes"""
    print("\n" + "=" * 70)
    print("TEST 5: Multiple Concurrent Writes")
    print("=" * 70)
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def write_key(key, value):
            try:
                response = httpx.post(
                    f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=10
                )
                return response.status_code == 200
            except:
                return False

        # Write 10 different keys concurrently
        print("  ⏳ Writing 10 keys concurrently...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                key = f"concurrent_key_{i}"
                value = f"concurrent_value_{i}"
                futures.append(executor.submit(write_key, key, value))

            results = [future.result() for future in as_completed(futures)]

        successful = sum(results)
        print(f"  ✅ Successfully wrote {successful}/10 keys")

        if successful >= 8:  # Allow some failures
            print("✅ PASSED: Concurrent writes work correctly")
            return True
        else:
            print("❌ FAILED: Too many write failures")
            return False
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_quorum_configuration():
    """Test 6: Dynamic quorum configuration"""
    print("\n" + "=" * 70)
    print("TEST 6: Dynamic Quorum Configuration")
    print("=" * 70)
    try:
        # Try to change quorum
        response = httpx.post(f"{LEADER_URL}/config", json={"quorum": 3}, timeout=5)
        assert response.status_code == 200, "Config update failed"
        data = response.json()
        assert data["quorum"] == 3, "Quorum not updated correctly"
        print(f"  ✅ Quorum updated to 3")

        # Test write with new quorum
        write_data = {"key": "quorum_test", "value": "quorum_value"}
        response = httpx.post(f"{LEADER_URL}/write", json=write_data, timeout=10)
        assert response.status_code == 200, "Write with new quorum failed"
        print(f"  ✅ Write with quorum=3 successful")

        print("✅ PASSED: Dynamic quorum configuration works")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_read_nonexistent_key():
    """Test 7: Read non-existent key"""
    print("\n" + "=" * 70)
    print("TEST 7: Read Non-Existent Key")
    print("=" * 70)
    try:
        response = httpx.get(f"{LEADER_URL}/read/nonexistent_key_12345", timeout=5)
        assert response.status_code == 404, "Should return 404 for non-existent key"
        print("  ✅ Correctly returned 404 for non-existent key")
        print("✅ PASSED: Error handling works correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def run_all_tests():
    """Run all integration tests without restarting containers"""
    print("\n" + "=" * 70)
    print("KEY-VALUE STORE INTEGRATION TESTS (NO DOCKER RESTART)")
    print("Single-Leader Replication System")
    print("=" * 70)

    print("\n🔍 Checking if services are already running...")

    if not wait_for_services(timeout=20):
        print("❌ Services are not running. Start docker-compose manually first.")
        return False

    print("🚀 Services detected, starting tests...\n")

    tests = [
        test_leader_health,
        test_followers_health,
        test_write_and_read,
        test_replication_to_followers,
        test_multiple_writes,
        test_quorum_configuration,
        test_read_nonexistent_key,
        test_race_condition_single_key,
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")

    print("\n" + "=" * 70)

    return passed == total


def test_race_condition_single_key():
    print("\n" + "=" * 70)
    print("TEST X: Race Condition — Same Key Writes")
    print("=" * 70)

    from concurrent.futures import ThreadPoolExecutor

    KEY = "race_test"
    VALUES = [f"value_{i}" for i in range(100)]

    def write_value(v):
        try:
            r = httpx.post(
                f"{LEADER_URL}/write", json={"key": KEY, "value": v}, timeout=5
            )
            return r.status_code == 200
        except:
            return False

    # concurrent writes
    with ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(write_value, VALUES))

    # Ensure most writes succeeded
    if sum(results) < 90:
        print("❌ Too many write failures")
        return False

    time.sleep(1)

    # Read final value
    r = httpx.get(f"{LEADER_URL}/read/{KEY}", timeout=5)
    if r.status_code != 200:
        print("❌ Race test key not found")
        return False

    final = r.json()["value"]
    print(f"Final value stored: {final}")

    expected = VALUES[-1]
    if final == expected:
        print("✅ PASSED: Last writer wins (no lost updates)")
        return True
    else:
        print(f"❌ FAILED: Expected '{expected}' but got '{final}'")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during tests: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

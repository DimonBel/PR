#!/usr/bin/env python3

import socket
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple
import sys


class ConcurrentTester:
    """Tests HTTP server performance with concurrent requests."""

    def __init__(self, host: str, port: int, server_name: str):
        self.host = host
        self.port = port
        self.server_name = server_name

    def _send_single_request(self, resource: str) -> Tuple[float, bool]:
        """
        Sends a single HTTP GET request and returns (time_taken, success).
        """
        start_time = time.time()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                request = f"GET /{resource} HTTP/1.1\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
                s.sendall(request.encode("utf-8"))

                # Receive the full response
                chunks = []
                while True:
                    data = s.recv(4096)
                    if not data:
                        break
                    chunks.append(data)

            elapsed = time.time() - start_time
            return elapsed, True
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Error requesting {resource}: {e}", file=sys.stderr)
            return elapsed, False

    def test_concurrent_requests(
        self, resource: str = "", num_requests: int = 10, num_workers: int = 10
    ) -> Tuple[float, int, List[float]]:
        """
        Makes concurrent requests to the server and measures performance.

        Args:
            resource: The resource path to request (default: root)
            num_requests: Number of concurrent requests
            num_workers: Number of worker threads (default: same as num_requests)
        
        Returns:
            Tuple of (overall_time, successful_requests, times_list)
        """
        print(f"\n{'='*70}")
        print(f"Testing: {self.server_name}")
        print(f"URL: http://{self.host}:{self.port}/{resource}")
        print(f"Concurrent requests: {num_requests}")
        print(f"{'='*70}\n")

        times: List[float] = []
        successful_requests = 0

        # Record the overall start time
        overall_start = time.time()

        # Use ThreadPoolExecutor to handle concurrent requests
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all requests
            futures = [
                executor.submit(self._send_single_request, resource)
                for _ in range(num_requests)
            ]

            # Collect results as they complete
            for i, future in enumerate(as_completed(futures), 1):
                elapsed, success = future.result()
                times.append(elapsed)
                if success:
                    successful_requests += 1
                print(
                    f"Request {i:2d}: {elapsed:.3f}s - {'✓' if success else '✗'}")

        overall_elapsed = time.time() - overall_start

        # Print statistics
        print(f"\n{'-'*70}")
        print(f"STATISTICS - {self.server_name}:")
        print(f"{'-'*70}")
        print(f"Successful requests: {successful_requests}/{num_requests}")
        print(f"Total time (wall-clock): {overall_elapsed:.3f}s")
        print(f"Average request time: {sum(times) / len(times):.3f}s")
        print(f"Min request time: {min(times):.3f}s")
        print(f"Max request time: {max(times):.3f}s")
        print(
            f"Throughput: {num_requests / overall_elapsed:.2f} requests/second")
        print(f"{'-'*70}\n")

        return overall_elapsed, successful_requests, times


def compare_servers(
    single_host: str, 
    single_port: int,
    multi_host: str,
    multi_port: int,
    resource: str = "",
    num_requests: int = 10
) -> None:
    """
    Compares performance between single-threaded and multi-threaded servers.
    """
    print("\n" + "="*70)
    print("SERVER PERFORMANCE COMPARISON TEST")
    print("="*70)
    
    # Test single-threaded server
    single_tester = ConcurrentTester(single_host, single_port, "Single-Threaded Server (lab1)")
    single_time, single_success, single_times = single_tester.test_concurrent_requests(
        resource=resource, 
        num_requests=num_requests
    )
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test multi-threaded server
    multi_tester = ConcurrentTester(multi_host, multi_port, "Multi-Threaded Server (Concurrent)")
    multi_time, multi_success, multi_times = multi_tester.test_concurrent_requests(
        resource=resource,
        num_requests=num_requests
    )
    
    # Print comparison
    print(f"\n{'='*70}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*70}\n")
    
    print(f"{'Metric':<30} {'Single-Threaded':<20} {'Multi-Threaded':<20}")
    print("-" * 70)
    print(f"{'Total Time':<30} {single_time:.3f}s{'':<14} {multi_time:.3f}s")
    print(f"{'Average Response Time':<30} {sum(single_times)/len(single_times):.3f}s{'':<14} {sum(multi_times)/len(multi_times):.3f}s")
    print(f"{'Min Response Time':<30} {min(single_times):.3f}s{'':<14} {min(multi_times):.3f}s")
    print(f"{'Max Response Time':<30} {max(single_times):.3f}s{'':<14} {max(multi_times):.3f}s")
    print(f"{'Throughput':<30} {num_requests/single_time:.2f} req/s{'':<11} {num_requests/multi_time:.2f} req/s")
    print(f"{'Successful Requests':<30} {single_success}/{num_requests}{'':<14} {multi_success}/{num_requests}")
    
    # Calculate speedup
    if single_time > 0 and multi_time > 0:
        speedup = single_time / multi_time
        print(f"\n{'='*70}")
        if speedup > 1:
            print(f"Multi-threaded server is {speedup:.2f}x FASTER than single-threaded")
        elif speedup < 1:
            print(f"Single-threaded server is {1/speedup:.2f}x FASTER than multi-threaded")
        else:
            print(f"Both servers have similar performance")
        print(f"Time saved: {abs(single_time - multi_time):.3f}s ({abs(single_time - multi_time)/single_time*100:.1f}%)")
        print(f"{'='*70}\n")


def main():
    """Main function to run concurrent tests."""
    
    # Default configuration for your servers
    SINGLE_THREADED_HOST = "localhost"
    SINGLE_THREADED_PORT = 2222
    
    MULTI_THREADED_HOST = "localhost"
    MULTI_THREADED_PORT = 3333
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage: python test_concurrent.py [resource] [num_requests]")
            print("\nDefault servers:")
            print(f"  Single-threaded: http://{SINGLE_THREADED_HOST}:{SINGLE_THREADED_PORT}/")
            print(f"  Multi-threaded:  http://{MULTI_THREADED_HOST}:{MULTI_THREADED_PORT}/")
            print("\nExamples:")
            print("  python test_concurrent.py")
            print("  python test_concurrent.py '' 10")
            print("  python test_concurrent.py 'images' 20")
            sys.exit(0)
    
    resource = sys.argv[1] if len(sys.argv) > 1 else ""
    num_requests = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    # Run comparison test
    compare_servers(
        SINGLE_THREADED_HOST,
        SINGLE_THREADED_PORT,
        MULTI_THREADED_HOST,
        MULTI_THREADED_PORT,
        resource=resource,
        num_requests=num_requests
    )


if __name__ == "__main__":
    main()
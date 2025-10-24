#!/usr/bin/env python3
import threading
import time
import http.client
from urllib.parse import urlparse
from collections import defaultdict


def do_request(url: str, results: dict, idx: int):
    parsed = urlparse(url)
    host = parsed.hostname or 'localhost'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    path = parsed.path or '/'
    if parsed.query:
        path += '?' + parsed.query

    if parsed.scheme == 'https':
        conn = http.client.HTTPSConnection(host, port, timeout=10)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=10)

    try:
        conn.request('GET', path)
        resp = conn.getresponse()
        body = resp.read()
        results[idx] = (resp.status, len(body))
    except Exception:
        results[idx] = (0, 0)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_concurrency(url: str, n: int):
    results = {}
    threads = [threading.Thread(target=do_request, args=(url, results, i)) for i in range(n)]
    t0 = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.time() - t0
    status_count = defaultdict(int)
    for status, _ in results.values():
        status_count[status] += 1  # Fix the bug here
    print(f"Completed {n} requests in {elapsed:.2f}s")
    for st in sorted(status_count.keys()):
        print(f"  {st}: {status_count[st]}")

def main():
    # url = 'http://localhost:8080/'  
    url = 'http://localhost:3333'
    concurrency = 22  #requests
    

    print(f"Running {concurrency} concurrent requests to {url}")
    run_concurrency(url, concurrency)


if __name__ == '__main__':
    main()
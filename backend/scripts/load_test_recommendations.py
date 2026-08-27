"""Conservative dependency-free HTTP load checker for safe cached/read paths."""

import argparse
import math
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


SAFE_PATHS = {"/health", "/ready", "/openapi.json"}


def percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percent) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", default="/health")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--token")
    parser.add_argument("--allow-remote-target", action="store_true")
    parser.add_argument("--allow-authenticated-cache-path", action="store_true")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        parser.error("--base-url must be a complete HTTP(S) URL")
    if parsed.hostname not in {"localhost", "127.0.0.1"} and not args.allow_remote_target:
        parser.error("Remote targets require --allow-remote-target")
    if args.path not in SAFE_PATHS and not args.allow_authenticated_cache_path:
        parser.error("Non-health paths require --allow-authenticated-cache-path")
    if "/ranked" in args.path:
        parser.error("Uncached ranked recommendation load testing is prohibited")
    if not 1 <= args.requests <= 500 or not 1 <= args.concurrency <= 20:
        parser.error("Safe limits: requests 1-500, concurrency 1-20")

    def one() -> tuple[int, float]:
        headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
        started = time.perf_counter()
        try:
            with urlopen(Request(args.base_url.rstrip("/") + args.path, headers=headers), timeout=20) as response:
                status = response.status; response.read()
        except HTTPError as error:
            status = error.code
        except URLError:
            status = 0
        return status, (time.perf_counter() - started) * 1_000

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda _item: one(), range(args.requests)))
    elapsed = time.perf_counter() - started
    statuses = Counter(status for status, _ in results)
    latencies = [latency for _, latency in results]
    success = sum(count for status, count in statuses.items() if 200 <= status < 300)
    rate_limited = statuses.get(429, 0)
    failures = args.requests - success - rate_limited
    print(f"Target: {args.base_url.rstrip('/')}{args.path}")
    print(f"Concurrency: {args.concurrency}\nRequests: {args.requests}\nSuccess: {success}")
    print(f"HTTP 429: {rate_limited}\nFailures: {failures}\nStatuses: {dict(statuses)}")
    print(f"Average ms: {statistics.mean(latencies):.2f}\nMedian ms: {statistics.median(latencies):.2f}")
    print(f"P95 ms: {percentile(latencies, .95):.2f}\nMax ms: {max(latencies):.2f}")
    print(f"Requests/sec: {args.requests / elapsed:.2f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

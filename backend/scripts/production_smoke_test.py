"""Safe HTTP smoke checks for a deployed DhakaNest backend."""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(base_url: str, path: str, token: str | None = None) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(base_url.rstrip("/") + path, headers=headers), timeout=15) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"null")
    except URLError as error:
        raise RuntimeError("Smoke target is unreachable.") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", help="Explicit non-production test token.")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    checks = [("liveness", "/health", {200}), ("readiness", "/ready", {200}),
              ("openapi", "/openapi.json", {200})]
    if args.token:
        checks.append(("authentication", "/auth/me", {200}))
        checks.append(("history", "/api/recommendations/history?page=1&page_size=1", {200}))
        if args.run_id:
            checks.append(("history detail", f"/api/recommendations/history/{args.run_id}", {200}))
    blocked = False
    for name, path, accepted in checks:
        status, _payload = request(args.base_url, path, args.token)
        outcome = "PASS" if status in accepted else "BLOCKED"
        blocked |= outcome == "BLOCKED"
        print(f"{outcome:<7} {name}: HTTP {status}")
    if not args.token:
        print("WARNING Authenticated checks skipped; no explicit test token supplied.")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())

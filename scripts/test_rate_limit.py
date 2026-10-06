"""Script to test and verify the IP rate limiter by firing 110 rapid requests."""

import json
import httpx

TARGET_URL = "http://127.0.0.1:8000/api/v1/restaurants?limit=1"
TOTAL_REQUESTS = 110


def test_rate_limiter() -> None:
    """Send 110 rapid requests to trigger and verify rate limiting (HTTP 429)."""
    print(f"Firing {TOTAL_REQUESTS} rapid requests to {TARGET_URL}...\n")

    count_200 = 0
    count_429 = 0
    first_429_reported = False

    with httpx.Client(timeout=10.0) as client:
        for i in range(1, TOTAL_REQUESTS + 1):
            response = client.get(TARGET_URL)
            status = response.status_code

            if status == 200:
                count_200 += 1
                if i % 20 == 0 or i == 1 or i == 100:
                    remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
                    print(f"Request #{i:03d}: HTTP {status} (Remaining: {remaining})")

            elif status == 429:
                count_429 += 1
                if not first_429_reported:
                    first_429_reported = True
                    print(f"\n[!] Rate Limit Triggered at Request #{i:03d}!")
                    print(f"    Status Code: HTTP {status}")
                    print(f"    Retry-After Header: {response.headers.get('Retry-After')}")
                    print(f"    X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit')}")
                    print(f"    X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining')}")
                    print(f"    X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset')}")
                    print("    Response Body Envelope:")
                    try:
                        print(f"    {json.dumps(response.json(), indent=6)}")
                    except Exception:
                        print(f"    {response.text}")
                    print()
                else:
                    if i == TOTAL_REQUESTS:
                        print(f"Request #{i:03d}: HTTP {status} (Still throttled)")
            else:
                print(f"Request #{i:03d}: HTTP {status}")

    print("\n--- Summary ---")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Successful (HTTP 200): {count_200}")
    print(f"Throttled (HTTP 429):  {count_429}")

    if count_429 > 0:
        print("[SUCCESS] Rate limiter successfully throttled excess requests with HTTP 429.")
    else:
        print("[NOTICE] Quota was not exhausted within 110 requests.")


if __name__ == "__main__":
    test_rate_limiter()

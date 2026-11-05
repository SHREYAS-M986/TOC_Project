import json
import urllib.error
import urllib.request

BASE = "https://toc-project-six.vercel.app"

endpoints = [
    ("/api/health", "GET", None),
    ("/api/pages", "GET", None),
    ("/api/pages/page1", "GET", None),
    ("/api/patterns", "GET", None),
    ("/api/summary", "GET", None),
    ("/api/dfa/definition", "GET", None),
    ("/api/testcases", "GET", None),
    (
        "/api/analyze/re",
        "POST",
        {"text": "Contact us at alice@example.com or +91 98765 43210 on 15/08/2024"},
    ),
    (
        "/api/analyze/dfa",
        "POST",
        {"text": "Contact us at alice@example.com or +91 98765 43210 on 15/08/2024"},
    ),
    ("/api/dfa/trace", "POST", {"word": "user@domain.com"}),
    ("/api/compare", "POST", {"page_id": "page1", "re_runs": 3, "dfa_runs": 3}),
]

print(f"Testing Live Deployment at: {BASE}\n" + "=" * 60)
all_passed = True
for path, method, payload in endpoints:
    url = BASE + path
    headers = {"Content-Type": "application/json"} if payload else {}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8")
            res_data = json.loads(body)
            sample = (
                list(res_data.keys())
                if isinstance(res_data, dict)
                else f"len={len(res_data)}"
            )
            print(f"[PASS] {method:<4} {path:<30} -> {res.status} | {sample}")
    except urllib.error.HTTPError as e:
        all_passed = False
        err_msg = e.read().decode("utf-8", errors="replace")[:300]
        print(f"[FAIL] {method:<4} {path:<30} -> HTTP {e.code}: {err_msg}")
    except Exception as e:
        all_passed = False
        print(f"[ERROR] {method:<4} {path:<30} -> {e}")

print("=" * 60)
if all_passed:
    print("ALL LIVE ENDPOINTS PASSED SUCCESSFULLY!")
else:
    print("SOME ENDPOINTS FAILED!")

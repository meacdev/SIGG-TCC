"""Small HTTP load probe. Token is read only from the environment, never printed."""

import argparse
import json
import math
import os
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--users", type=int, default=50)
parser.add_argument("--requests", type=int, default=200)
parser.add_argument("--create-course-id", type=int)
parser.add_argument("--teacher-id", type=int)
parser.add_argument("--period", default="2026/2")
args = parser.parse_args()
url = os.environ["SIGG_LOAD_URL"]
token = os.environ["SIGG_LOAD_TOKEN"]
if args.users < 1 or args.requests < 1:
    parser.error("users and requests must be positive")
if args.create_course_id and not args.teacher_id:
    parser.error("--teacher-id is required for class creation")
prefix = str(secrets.randbelow(10**10))


def call(index):
    start = time.perf_counter()
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if args.create_course_id:
        data = json.dumps(
            {
                "periodo_letivo": args.period,
                "codigo_turma": f"ESTLOAD{prefix}{index}",
                "nivel_turma": 1,
                "id_curso": args.create_course_id,
                "id_docente_responsavel": args.teacher_id,
            }
        ).encode()
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=data, headers=headers), timeout=15) as response:
            response.read()
            status = response.status
    except HTTPError as error:
        status = error.code
    except URLError, TimeoutError:
        status = 0
    return time.perf_counter() - start, status


start = time.perf_counter()
with ThreadPoolExecutor(max_workers=args.users) as pool:
    results = list(pool.map(call, range(args.requests)))
elapsed = time.perf_counter() - start
times = sorted(duration for duration, _ in results)
p95 = times[max(0, math.ceil(len(times) * 0.95) - 1)]
failures = sum(not 200 <= status < 300 for _, status in results)
print(
    json.dumps(
        {
            "concurrent_users": args.users,
            "requests": len(results),
            "failures": failures,
            "p95_seconds": round(p95, 4),
            "mean_seconds": round(statistics.mean(times), 4),
            "requests_per_second": round(len(results) / elapsed, 2),
        },
        indent=2,
    )
)
raise SystemExit(1 if failures or p95 > 2 else 0)

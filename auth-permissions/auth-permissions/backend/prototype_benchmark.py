import argparse
import csv
import json
import os
import random
import statistics
import time
from datetime import datetime, timezone
from urllib import error, request


API_BASE = os.getenv("API_BASE", "http://localhost:5000/api")
MATIC_USD_PRICE = float(os.getenv("MATIC_USD_PRICE", "0"))
ACTIONS = ["read", "write", "update", "delete", "export", "admin"]

TEST_USERS = [
    {
        "name": "Benchmark User A",
        "email": "bench_user_a@local.test",
        "password": "benchpass123",
        "permissions": ["read", "write"],
        "is_auditor": False,
    },
    {
        "name": "Benchmark User B",
        "email": "bench_user_b@local.test",
        "password": "benchpass123",
        "permissions": ["read", "update", "export"],
        "is_auditor": False,
    },
    {
        "name": "Benchmark User C",
        "email": "bench_user_c@local.test",
        "password": "benchpass123",
        "permissions": ["delete"],
        "is_auditor": False,
    },
    {
        "name": "Benchmark Auditor",
        "email": "bench_auditor@local.test",
        "password": "benchpass123",
        "permissions": ["read"],
        "is_auditor": True,
    },
]


def api_call(path: str, method: str = "GET", token: str | None = None, payload: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(f"{API_BASE}{path}", data=body, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=30) as resp:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}, elapsed_ms
    except error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        raw = e.read().decode("utf-8") if e.fp else ""
        data = json.loads(raw) if raw else {}
        return e.code, data, elapsed_ms


def ensure_users():
    for user in TEST_USERS:
        api_call(
            "/auth/register",
            method="POST",
            payload={
                "name": user["name"],
                "email": user["email"],
                "password": user["password"],
                "permissions": user["permissions"],
                "is_auditor": user["is_auditor"],
            },
        )


def login_users():
    sessions = []
    for user in TEST_USERS:
        status, data, _ = api_call(
            "/auth/login",
            method="POST",
            payload={"email": user["email"], "password": user["password"]},
        )
        if status != 200:
            raise RuntimeError(f"Login failed for {user['email']}: {data}")
        sessions.append({"profile": user, "token": data["token"], "user": data["user"]})
    return sessions


def summarize(values: list[float]):
    if not values:
        return {"avg": None, "min": None, "max": None}
    return {
        "avg": round(statistics.mean(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def run_benchmark(rounds_per_user: int, seed: int):
    random.seed(seed)

    health_status, health_data, _ = api_call("/health")
    if health_status != 200:
        raise RuntimeError("Backend health endpoint is not reachable.")

    ensure_users()
    sessions = login_users()

    normal_sessions = [s for s in sessions if not s["user"]["is_auditor"]]
    auditor_session = next(s for s in sessions if s["user"]["is_auditor"])

    attempts = []
    unauthorized_rows = []

    for session in normal_sessions:
        user = session["user"]
        token = session["token"]

        for _ in range(rounds_per_user):
            action = random.choice(ACTIONS)
            authorized = action in user["permissions"]

            if authorized:
                attempts.append(
                    {
                        "user_id": user["id"],
                        "user_name": user["name"],
                        "action": action,
                        "authorized": True,
                        "detected": None,
                        "status_code": None,
                        "api_roundtrip_ms": None,
                        "backend_processing_ms": None,
                        "gas_used": None,
                        "estimated_cost_matic": None,
                        "tx_hash": None,
                        "logical_payload_bytes": None,
                        "tx_input_size_bytes": None,
                        "error": None,
                    }
                )
                continue

            status, data, api_ms = api_call(
                "/violation",
                method="POST",
                token=token,
                payload={"action": action},
            )

            detected = status in (201, 202)
            row = {
                "user_id": user["id"],
                "user_name": user["name"],
                "action": action,
                "authorized": False,
                "detected": detected,
                "status_code": status,
                "api_roundtrip_ms": round(api_ms, 3),
                "backend_processing_ms": data.get("processing_ms"),
                "gas_used": data.get("gas_used"),
                "estimated_cost_matic": data.get("estimated_cost_matic"),
                "tx_hash": data.get("tx_hash"),
                "logical_payload_bytes": data.get("logical_payload_bytes"),
                "tx_input_size_bytes": data.get("tx_input_size_bytes"),
                "error": data.get("error"),
            }
            attempts.append(row)
            unauthorized_rows.append(row)

    # Read runtime summary from backend collector
    metrics_status, metrics_data, _ = api_call(
        "/metrics/summary",
        token=auditor_session["token"],
    )
    if metrics_status != 200:
        metrics_data = {"error": "could not read /metrics/summary"}

    # Aggregate benchmark-only stats
    total_attempts = len(attempts)
    authorized_attempts = sum(1 for x in attempts if x["authorized"])
    unauthorized_attempts = sum(1 for x in attempts if not x["authorized"])
    detected_violations = sum(1 for x in attempts if x["detected"] is True)

    detection_rate = (detected_violations / unauthorized_attempts) if unauthorized_attempts else 0.0
    onchain_success = sum(1 for x in unauthorized_rows if x["status_code"] == 201)
    onchain_success_rate = (onchain_success / unauthorized_attempts) if unauthorized_attempts else 0.0

    api_latencies = [x["api_roundtrip_ms"] for x in unauthorized_rows if x["api_roundtrip_ms"] is not None]
    backend_latencies = [float(x["backend_processing_ms"]) for x in unauthorized_rows if x["backend_processing_ms"] is not None]
    gas_values = [int(x["gas_used"]) for x in unauthorized_rows if x["gas_used"] is not None]
    costs_matic = [float(x["estimated_cost_matic"]) for x in unauthorized_rows if x["estimated_cost_matic"] is not None]
    payload_values = [int(x["logical_payload_bytes"]) for x in unauthorized_rows if x["logical_payload_bytes"] is not None]
    input_values = [int(x["tx_input_size_bytes"]) for x in unauthorized_rows if x["tx_input_size_bytes"] is not None]

    costs_usd = [c * MATIC_USD_PRICE for c in costs_matic] if MATIC_USD_PRICE > 0 else []

    report = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "api_base": API_BASE,
            "blockchain_connected": health_data.get("blockchain"),
            "actions_catalog": ACTIONS,
            "users_in_experiment": len(normal_sessions),
            "rounds_per_user": rounds_per_user,
            "random_seed": seed,
        },
        "benchmark_summary": {
            "total_attempts": total_attempts,
            "authorized_attempts": authorized_attempts,
            "unauthorized_attempts": unauthorized_attempts,
            "detected_violations": detected_violations,
            "detection_rate": round(detection_rate, 6),
            "onchain_success_rate": round(onchain_success_rate, 6),
            "api_roundtrip_ms": summarize(api_latencies),
            "backend_processing_ms": summarize(backend_latencies),
            "gas_used": summarize(gas_values),
            "estimated_cost_matic": summarize(costs_matic),
            "estimated_cost_usd": summarize(costs_usd),
            "logical_payload_bytes": summarize(payload_values),
            "tx_input_size_bytes": summarize(input_values),
        },
        "backend_runtime_summary": metrics_data,
    }

    return report, attempts


def save_outputs(report: dict, attempts: list[dict]):
    base_dir = os.path.dirname(__file__)
    out_dir = os.path.join(base_dir, "metrics_reports")
    os.makedirs(out_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(out_dir, f"benchmark_report_{stamp}.json")
    csv_path = os.path.join(out_dir, f"benchmark_attempts_{stamp}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    fieldnames = [
        "user_id",
        "user_name",
        "action",
        "authorized",
        "detected",
        "status_code",
        "api_roundtrip_ms",
        "backend_processing_ms",
        "gas_used",
        "estimated_cost_matic",
        "tx_hash",
        "logical_payload_bytes",
        "tx_input_size_bytes",
        "error",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in attempts:
            writer.writerow(row)

    return json_path, csv_path


def main():
    parser = argparse.ArgumentParser(description="Runs a quantitative benchmark for the prototype.")
    parser.add_argument("--rounds-per-user", type=int, default=30, help="How many random attempts per non-auditor user")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    report, attempts = run_benchmark(args.rounds_per_user, args.seed)
    json_path, csv_path = save_outputs(report, attempts)

    print("Benchmark completed.")
    print(f"Report JSON: {json_path}")
    print(f"Raw CSV:     {csv_path}")
    print("\nKey numbers:")
    summary = report["benchmark_summary"]
    print(f"- users_in_experiment: {report['environment']['users_in_experiment']}")
    print(f"- total_attempts: {summary['total_attempts']}")
    print(f"- authorized_attempts: {summary['authorized_attempts']}")
    print(f"- unauthorized_attempts: {summary['unauthorized_attempts']}")
    print(f"- detection_rate: {summary['detection_rate']}")
    print(f"- onchain_success_rate: {summary['onchain_success_rate']}")
    print(f"- api_roundtrip_ms_avg: {summary['api_roundtrip_ms']['avg']}")
    print(f"- backend_processing_ms_avg: {summary['backend_processing_ms']['avg']}")
    print(f"- gas_used_avg: {summary['gas_used']['avg']}")
    print(f"- estimated_cost_matic_avg: {summary['estimated_cost_matic']['avg']}")


if __name__ == "__main__":
    main()

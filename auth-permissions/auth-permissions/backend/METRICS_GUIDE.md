# Quantitative Metrics Guide (Prototype)

This guide defines which metrics to report in a scientific paper and how to collect them from this prototype.

## Recommended Metrics

1. Test scenario size
- Number of test users
- Number of available actions (`read`, `write`, `update`, `delete`, `export`, `admin`)
- Number of total attempts
- Number of authorized attempts
- Number of unauthorized attempts

2. Detection effectiveness
- Detected violations
- Detection rate

Formula:

$$
\text{Detection Rate} = \frac{\text{Detected Violations}}{\text{Unauthorized Attempts}}
$$

3. Performance
- API roundtrip latency (ms): avg, min, max
- Backend processing latency (ms): avg, min, max

4. Blockchain overhead
- Gas used per violation tx: avg, min, max
- Estimated cost in MATIC: avg, min, max
- Estimated cost in USD (optional, with `MATIC_USD_PRICE` env)
- Logical payload size (bytes)
- Transaction input size (bytes)

5. Operational reliability
- On-chain success rate
- Blockchain confirmed vs not confirmed

## Implemented Collection

### 1) Runtime collector in backend
- File: `metrics.py`
- Event log: `metrics_data/violation_events.jsonl`

Each denied action sent to `/api/violation` now stores:
- timestamps
- action and user
- processing time
- tx hash/block
- gas used and gas price
- estimated cost
- payload sizes
- error details

### 2) Metrics endpoints (auditor only)
- `GET /api/metrics/summary`
- `GET /api/metrics/events`

### 3) Reproducible benchmark script
- File: `prototype_benchmark.py`
- Outputs:
  - `metrics_reports/benchmark_report_YYYYMMDD_HHMMSS.json`
  - `metrics_reports/benchmark_attempts_YYYYMMDD_HHMMSS.csv`

## How to Run

From backend directory:

```powershell
$env:API_BASE="http://127.0.0.1:5000/api"
# optional for Polygon cost in USD
$env:MATIC_USD_PRICE="0.70"
python prototype_benchmark.py --rounds-per-user 30 --seed 42
```

Use larger `--rounds-per-user` (for example 50, 100, 200) to increase statistical confidence.

## Suggested Tables for the Paper

1. Experimental setup
- users, actions, attempts, blockchain mode (Hardhat local or Polygon)

2. Detection results
- unauthorized attempts, detected violations, detection rate

3. Latency results
- API roundtrip avg/min/max
- backend processing avg/min/max

4. Blockchain cost results
- gas avg/min/max
- estimated MATIC cost avg/min/max
- estimated USD avg/min/max
- payload size avg/min/max

## Notes

- In Hardhat local, gas price can be near zero, so MATIC cost may appear as zero.
- For realistic financial cost, run the same benchmark on Polygon testnet/mainnet RPC and set `MATIC_USD_PRICE`.

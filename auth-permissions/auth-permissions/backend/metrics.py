import json
import os
from datetime import datetime, timezone
from statistics import mean


class MetricsCollector:
    """Collects violation/runtime metrics and persists event logs as JSONL."""

    def __init__(self):
        self._events = []
        base_dir = os.path.dirname(__file__)
        self.metrics_dir = os.path.join(base_dir, "metrics_data")
        os.makedirs(self.metrics_dir, exist_ok=True)
        self.events_file = os.path.join(self.metrics_dir, "violation_events.jsonl")

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    def record_violation_event(self, event: dict):
        payload = dict(event)
        payload["recorded_at"] = self._now_iso()
        self._events.append(payload)
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def summary(self) -> dict:
        events = self._events
        total = len(events)

        chain_ok = [e for e in events if e.get("blockchain_confirmed")]
        chain_fail = [e for e in events if not e.get("blockchain_confirmed")]

        latencies = [float(e["processing_ms"]) for e in events if e.get("processing_ms") is not None]
        gas_used = [int(e["gas_used"]) for e in events if e.get("gas_used") is not None]
        payload_sizes = [int(e["logical_payload_bytes"]) for e in events if e.get("logical_payload_bytes") is not None]
        tx_input_sizes = [int(e["tx_input_size_bytes"]) for e in events if e.get("tx_input_size_bytes") is not None]
        costs_matic = [float(e["estimated_cost_matic"]) for e in events if e.get("estimated_cost_matic") is not None]

        detected = sum(1 for e in events if e.get("detected_violation"))
        simulated_unauthorized = total
        detection_rate = (detected / simulated_unauthorized) if simulated_unauthorized else 0.0

        return {
            "events_total": total,
            "detected_violations": detected,
            "simulated_unauthorized_attempts": simulated_unauthorized,
            "detection_rate": round(detection_rate, 6),
            "blockchain_confirmed": len(chain_ok),
            "blockchain_not_confirmed": len(chain_fail),
            "processing_ms_avg": round(mean(latencies), 3) if latencies else None,
            "processing_ms_min": round(min(latencies), 3) if latencies else None,
            "processing_ms_max": round(max(latencies), 3) if latencies else None,
            "gas_used_avg": round(mean(gas_used), 2) if gas_used else None,
            "gas_used_min": min(gas_used) if gas_used else None,
            "gas_used_max": max(gas_used) if gas_used else None,
            "estimated_cost_matic_avg": round(mean(costs_matic), 8) if costs_matic else None,
            "logical_payload_bytes_avg": round(mean(payload_sizes), 2) if payload_sizes else None,
            "tx_input_size_bytes_avg": round(mean(tx_input_sizes), 2) if tx_input_sizes else None,
            "events_file": self.events_file,
        }


metrics = MetricsCollector()

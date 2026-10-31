import time
import random
import threading
from typing import Dict, Any, List
from engine import models
from engine import evaluator

class TrafficSimulator:
    """
    Background simulation engine that generates realistic microservice traffic,
    evaluates SLA/SLO compliance on every tick, and records alerts.
    """

    def __init__(self, db_path: str, interval_sec: float = 2.0):
        self.db_path = db_path
        self.interval_sec = interval_sec
        self.running = False
        self.paused = False
        self.thread = None
        self._lock = threading.Lock()
        self.tick_count = 0

    def start(self):
        """Start the background simulator thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
            self.paused = False
            self.thread = threading.Thread(target=self._run_loop, daemon=True, name="SLA-TrafficSimulator")
            self.thread.start()

    def stop(self):
        """Stop background simulator loop."""
        with self._lock:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)

    def pause(self):
        """Pause traffic generation."""
        self.paused = True

    def resume(self):
        """Resume traffic generation."""
        self.paused = False

    def is_running(self) -> bool:
        return self.running and not self.paused

    def _run_loop(self):
        """Internal background loop."""
        while self.running:
            if not self.paused:
                try:
                    self.step_tick()
                except Exception as e:
                    # In production simulator, continue ticking even if a transient DB lock occurs
                    print(f"[Simulator Warning] Error during tick: {e}")
            time.sleep(self.interval_sec)

    def step_tick(self) -> List[Dict[str, Any]]:
        """
        Execute a single tick of traffic generation for all services.
        Can be called by background thread or synchronously in tests.
        """
        self.tick_count += 1
        services = models.get_all_services(self.db_path)
        configs = {c["service_id"]: c for c in models.get_simulation_configs(self.db_path)}
        generated_samples = []

        now = time.time()

        for svc in services:
            svc_id = svc["id"]
            cfg = configs.get(svc_id, {"mode": "NORMAL", "base_qps": 100, "error_injection_pct": 0.0, "added_latency_ms": 0.0})
            
            sample = self._generate_sample_for_service(svc, cfg, now)
            
            # Retrieve SLO definitions for this service
            slos = models.get_service_slos(self.db_path, svc_id)
            
            # Evaluate SLOs
            eval_result = evaluator.evaluate_service_slos(sample, slos)
            sample["status"] = eval_result["overall_status"]
            sample_id = models.insert_metric_sample(self.db_path, sample)
            sample["id"] = sample_id

            # Alert Management
            self._process_alerts(svc, eval_result["slo_evaluations"], now)

            generated_samples.append(sample)

        # Periodic pruning every 50 ticks to keep database clean
        if self.tick_count % 50 == 0:
            try:
                models.prune_old_metrics(self.db_path, max_samples_per_service=300)
            except Exception:
                pass

        return generated_samples

    def _generate_sample_for_service(self, svc: Dict[str, Any], cfg: Dict[str, Any], timestamp: float) -> Dict[str, Any]:
        """Synthesize realistic metrics based on service profile and active simulation mode."""
        mode = cfg.get("mode", "NORMAL")
        base_qps = cfg.get("base_qps", 100)
        injected_errors = float(cfg.get("error_injection_pct", 0.0))
        added_latency = float(cfg.get("added_latency_ms", 0.0))

        # Base parameters depending on service tier
        tier = svc.get("tier", "Tier 2")
        if "Tier 1" in tier:
            baseline_latency = random.uniform(35.0, 75.0)
            baseline_err_rate = random.uniform(0.01, 0.08) # 99.92%+ availability
        elif "Tier 2" in tier:
            baseline_latency = random.uniform(80.0, 160.0)
            baseline_err_rate = random.uniform(0.05, 0.25) # 99.75%+ availability
        else:
            baseline_latency = random.uniform(150.0, 300.0)
            baseline_err_rate = random.uniform(0.2, 0.7)

        # Adjust for simulation modes
        multiplier_qps = 1.0
        final_added_latency = added_latency
        final_injected_errors = injected_errors

        if mode == "TRAFFIC_SPIKE":
            multiplier_qps = random.uniform(4.0, 8.0)
            final_added_latency += random.uniform(60.0, 140.0)
            final_injected_errors += random.uniform(0.5, 1.8)
        elif mode == "LATENCY_SPIKE":
            multiplier_qps = random.uniform(0.8, 1.2)
            final_added_latency += random.uniform(500.0, 1200.0)
        elif mode == "ERROR_FLOOD":
            multiplier_qps = random.uniform(1.2, 2.0)
            final_injected_errors += random.uniform(18.0, 35.0)
            final_added_latency += random.uniform(100.0, 300.0)
        elif mode == "PARTIAL_OUTAGE":
            multiplier_qps = random.uniform(0.5, 1.0)
            final_injected_errors += random.uniform(45.0, 65.0)
            final_added_latency += random.uniform(350.0, 800.0)
        elif mode == "TOTAL_OUTAGE":
            multiplier_qps = random.uniform(0.2, 0.6)
            final_injected_errors = 100.0
            final_added_latency += random.uniform(1500.0, 3000.0)
        elif mode == "FLAPPING":
            # Alternates every 4 ticks
            if (self.tick_count // 4) % 2 == 1:
                final_injected_errors += random.uniform(25.0, 50.0)
                final_added_latency += random.uniform(400.0, 900.0)

        # Compute request counts for the tick interval
        requests_in_tick = max(5, int(base_qps * multiplier_qps * self.interval_sec))
        
        # Calculate failure percentage
        total_error_pct = min(100.0, max(0.0, baseline_err_rate + final_injected_errors))
        failed_requests = int(round((total_error_pct / 100.0) * requests_in_tick))
        if total_error_pct > 0 and failed_requests == 0 and requests_in_tick > 0 and random.random() < (total_error_pct / 100.0):
            failed_requests = 1
        failed_requests = min(requests_in_tick, failed_requests)
        successful_requests = requests_in_tick - failed_requests

        # Calculate Latencies
        avg_latency = round(max(5.0, baseline_latency + final_added_latency + random.uniform(-10.0, 15.0)), 2)
        p95_latency = round(avg_latency * random.uniform(1.35, 1.65), 2)
        p99_latency = round(p95_latency * random.uniform(1.2, 1.5), 2)

        availability_pct = evaluator.calculate_availability(successful_requests, requests_in_tick)
        success_rate_pct = evaluator.calculate_success_rate(successful_requests, requests_in_tick)
        error_rate_pct = evaluator.calculate_error_rate(failed_requests, requests_in_tick)

        return {
            "timestamp": timestamp,
            "service_id": svc["id"],
            "total_requests": requests_in_tick,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "availability_pct": availability_pct,
            "success_rate_pct": success_rate_pct,
            "error_rate_pct": error_rate_pct,
        }

    def _process_alerts(self, svc: Dict[str, Any], evaluations: List[Dict[str, Any]], timestamp: float):
        """Evaluate each SLI result to trigger or resolve alerts."""
        svc_id = svc["id"]
        svc_name = svc["name"]

        for item in evaluations:
            sli_id = item["sli_id"]
            sli_name = item["sli_name"]
            status = item["status"]
            val = item["current_value"]
            target = item["slo_target"]
            unit = item["unit"]

            active_alert = models.get_active_alert_for_sli(self.db_path, svc_id, sli_id)

            if status in (evaluator.STATUS_WARNING, evaluator.STATUS_CRITICAL):
                severity = evaluator.SEVERITY_CRITICAL if status == evaluator.STATUS_CRITICAL else evaluator.SEVERITY_WARNING
                title = f"{status}: {svc_name} {sli_name} Breach"
                message = f"{sli_name} is currently {val:.2f}{unit} (Target SLO: {target:.2f}{unit}, SLA: {item['sla_target']:.2f}{unit}). {item['reason']}"

                if not active_alert:
                    # New alert
                    models.create_alert(self.db_path, {
                        "service_id": svc_id,
                        "sli_id": sli_id,
                        "severity": severity,
                        "title": title,
                        "message": message,
                        "current_value": val,
                        "threshold_value": item["warning_threshold"] if status == evaluator.STATUS_WARNING else item["sla_target"],
                        "created_at": timestamp
                    })
                elif active_alert["severity"] != severity:
                    # Severity escalated or downgraded
                    models.resolve_alerts_for_sli(self.db_path, svc_id, sli_id)
                    models.create_alert(self.db_path, {
                        "service_id": svc_id,
                        "sli_id": sli_id,
                        "severity": severity,
                        "title": title,
                        "message": message,
                        "current_value": val,
                        "threshold_value": item["warning_threshold"] if status == evaluator.STATUS_WARNING else item["sla_target"],
                        "created_at": timestamp
                    })
            else:
                # Healthy: resolve any open alert
                if active_alert:
                    models.resolve_alerts_for_sli(self.db_path, svc_id, sli_id)

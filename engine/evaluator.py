import math
import time
from typing import Dict, Any, List, Tuple

STATUS_HEALTHY = "HEALTHY"
STATUS_WARNING = "WARNING"
STATUS_CRITICAL = "CRITICAL"

SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"

def calculate_availability(good_requests: int, total_requests: int) -> float:
    """Calculate Availability SLI percentage (0.0 to 100.0)."""
    if total_requests <= 0:
        return 100.0
    good = max(0, min(good_requests, total_requests))
    return round((good / total_requests) * 100.0, 3)

def calculate_success_rate(successful_requests: int, total_requests: int) -> float:
    """Calculate Request Success Rate SLI percentage (0.0 to 100.0)."""
    if total_requests <= 0:
        return 100.0
    success = max(0, min(successful_requests, total_requests))
    return round((success / total_requests) * 100.0, 3)

def calculate_error_rate(failed_requests: int, total_requests: int) -> float:
    """Calculate Error Rate SLI percentage (0.0 to 100.0)."""
    if total_requests <= 0:
        return 0.0
    failed = max(0, min(failed_requests, total_requests))
    return round((failed / total_requests) * 100.0, 3)

def calculate_error_budget(slo_target: float, current_value: float, comparison_op: str = ">=") -> Dict[str, float]:
    """
    Calculate remaining Error Budget (%) and Error Budget Burn Rate.
    Returns:
        {
            "budget_remaining_pct": float (0.0 to 100.0),
            "burn_rate": float (e.g. 1.0 is on target, >1.0 burning too fast),
            "burned_pct": float (0.0 to 100.0)
        }
    """
    if comparison_op == ">=":
        # For availability / success rate, e.g. SLO is 99.9%
        allowable_failure = max(0.001, 100.0 - slo_target)
        actual_failure = max(0.0, 100.0 - current_value)
        burn_rate = round(actual_failure / allowable_failure, 2)
        
        fraction_consumed = actual_failure / allowable_failure
        budget_remaining = max(0.0, min(100.0, (1.0 - fraction_consumed) * 100.0))
        burned_pct = round(100.0 - budget_remaining, 2)
        return {
            "budget_remaining_pct": round(budget_remaining, 2),
            "burn_rate": burn_rate,
            "burned_pct": burned_pct
        }
    else:
        # For latency or error rate, e.g. SLO target <= 0.5% or <= 200ms
        target = max(0.001, slo_target)
        actual = max(0.0, current_value)
        burn_rate = round(actual / target, 2)

        fraction_consumed = actual / target
        budget_remaining = max(0.0, min(100.0, (1.0 - fraction_consumed) * 100.0))
        burned_pct = round(100.0 - budget_remaining, 2)
        return {
            "budget_remaining_pct": round(budget_remaining, 2),
            "burn_rate": burn_rate,
            "burned_pct": burned_pct
        }

def evaluate_slo_status(value: float, slo_target: float, warning_threshold: float, sla_target: float, comparison_op: str = ">=") -> Tuple[str, str]:
    """
    Evaluate metric value against SLO, Warning, and SLA thresholds.
    Returns (status, reason):
        status: HEALTHY, WARNING, or CRITICAL
        reason: Human readable explanation
    """
    if comparison_op == ">=":
        if value >= slo_target:
            return STATUS_HEALTHY, f"Metric value ({value:.2f}%) meets target SLO (>= {slo_target:.2f}%)"
        elif value >= sla_target:
            return STATUS_WARNING, f"Metric value ({value:.2f}%) is below SLO ({slo_target:.2f}%) but within SLA (>= {sla_target:.2f}%)"
        else:
            return STATUS_CRITICAL, f"CRITICAL: Metric value ({value:.2f}%) breached SLA threshold (< {sla_target:.2f}%)!"
    else: # "<="
        if value <= slo_target:
            return STATUS_HEALTHY, f"Metric value ({value:.2f}) meets target SLO (<= {slo_target:.2f})"
        elif value <= sla_target:
            return STATUS_WARNING, f"Metric value ({value:.2f}) exceeded SLO ({slo_target:.2f}) but within SLA (<= {sla_target:.2f})"
        else:
            return STATUS_CRITICAL, f"CRITICAL: Metric value ({value:.2f}) breached SLA threshold (> {sla_target:.2f})!"

def determine_overall_status(status_list: List[str]) -> str:
    """Determine highest severity status from a list of statuses."""
    if STATUS_CRITICAL in status_list:
        return STATUS_CRITICAL
    if STATUS_WARNING in status_list:
        return STATUS_WARNING
    return STATUS_HEALTHY

def evaluate_service_slos(metric_sample: Dict[str, Any], slo_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate all SLOs for a single service against the current metric sample.
    """
    results = []
    statuses = []

    metric_mapping = {
        "sli-availability": metric_sample.get("availability_pct", 100.0),
        "sli-success-rate": metric_sample.get("success_rate_pct", 100.0),
        "sli-response-time": metric_sample.get("p95_latency_ms", 0.0),
        "sli-error-rate": metric_sample.get("error_rate_pct", 0.0),
    }

    for slo in slo_list:
        sli_id = slo["sli_id"]
        current_val = metric_mapping.get(sli_id, 0.0)
        status, reason = evaluate_slo_status(
            value=current_val,
            slo_target=slo["slo_target"],
            warning_threshold=slo["warning_threshold"],
            sla_target=slo["sla_target"],
            comparison_op=slo.get("comparison_op", ">=")
        )
        statuses.append(status)

        budget_info = calculate_error_budget(
            slo_target=slo["slo_target"],
            current_value=current_val,
            comparison_op=slo.get("comparison_op", ">=")
        )

        results.append({
            "sli_id": sli_id,
            "sli_name": slo.get("sli_name", sli_id),
            "unit": slo.get("unit", ""),
            "current_value": current_val,
            "slo_target": slo["slo_target"],
            "warning_threshold": slo["warning_threshold"],
            "sla_target": slo["sla_target"],
            "comparison_op": slo.get("comparison_op", ">="),
            "status": status,
            "reason": reason,
            "error_budget": budget_info
        })

    overall_status = determine_overall_status(statuses)
    
    # Calculate average error budget remaining across SLOs
    avg_budget = 100.0
    if results:
        avg_budget = round(sum(r["error_budget"]["budget_remaining_pct"] for r in results) / len(results), 2)

    return {
        "overall_status": overall_status,
        "average_error_budget_pct": avg_budget,
        "slo_evaluations": results
    }

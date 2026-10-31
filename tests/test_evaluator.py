import pytest
from engine.evaluator import (
    calculate_availability,
    calculate_success_rate,
    calculate_error_rate,
    calculate_error_budget,
    evaluate_slo_status,
    determine_overall_status,
    evaluate_service_slos,
    STATUS_HEALTHY,
    STATUS_WARNING,
    STATUS_CRITICAL
)

def test_calculate_availability():
    assert calculate_availability(1000, 1000) == 100.0
    assert calculate_availability(999, 1000) == 99.9
    assert calculate_availability(990, 1000) == 99.0
    assert calculate_availability(0, 1000) == 0.0
    # Edge case: zero total requests
    assert calculate_availability(0, 0) == 100.0

def test_calculate_success_rate():
    assert calculate_success_rate(950, 1000) == 95.0
    assert calculate_success_rate(1000, 1000) == 100.0
    assert calculate_success_rate(0, 0) == 100.0

def test_calculate_error_rate():
    assert calculate_error_rate(5, 1000) == 0.5
    assert calculate_error_rate(0, 1000) == 0.0
    assert calculate_error_rate(100, 1000) == 10.0
    assert calculate_error_rate(0, 0) == 0.0

def test_calculate_error_budget_greater_equal():
    # Target SLO 99.0% -> allowable failure is 1.0%
    # Actual availability 99.5% -> actual failure is 0.5%
    # Remaining budget should be 50%
    budget = calculate_error_budget(slo_target=99.0, current_value=99.5, comparison_op=">=")
    assert budget["budget_remaining_pct"] == 50.0
    assert budget["burn_rate"] == 0.5
    assert budget["burned_pct"] == 50.0

    # Actual availability 98.0% (failure is 2.0% > allowable 1.0%)
    budget_exhausted = calculate_error_budget(slo_target=99.0, current_value=98.0, comparison_op=">=")
    assert budget_exhausted["budget_remaining_pct"] == 0.0
    assert budget_exhausted["burn_rate"] == 2.0

def test_calculate_error_budget_less_equal():
    # Latency SLO target <= 200ms
    # Current value = 100ms -> consumed 50%
    budget = calculate_error_budget(slo_target=200.0, current_value=100.0, comparison_op="<=")
    assert budget["budget_remaining_pct"] == 50.0
    assert budget["burn_rate"] == 0.5

def test_evaluate_slo_status_greater_equal():
    # Availability: Target 99.9%, Warning 99.5%, SLA 99.0%
    status, _ = evaluate_slo_status(99.95, slo_target=99.9, warning_threshold=99.5, sla_target=99.0, comparison_op=">=")
    assert status == STATUS_HEALTHY

    status, _ = evaluate_slo_status(99.4, slo_target=99.9, warning_threshold=99.5, sla_target=99.0, comparison_op=">=")
    assert status == STATUS_WARNING

    status, _ = evaluate_slo_status(98.5, slo_target=99.9, warning_threshold=99.5, sla_target=99.0, comparison_op=">=")
    assert status == STATUS_CRITICAL

def test_evaluate_slo_status_less_equal():
    # Latency: Target <= 150ms, Warning 250ms, SLA 400ms
    status, _ = evaluate_slo_status(120.0, slo_target=150.0, warning_threshold=250.0, sla_target=400.0, comparison_op="<=")
    assert status == STATUS_HEALTHY

    status, _ = evaluate_slo_status(200.0, slo_target=150.0, warning_threshold=250.0, sla_target=400.0, comparison_op="<=")
    assert status == STATUS_WARNING

    status, _ = evaluate_slo_status(500.0, slo_target=150.0, warning_threshold=250.0, sla_target=400.0, comparison_op="<=")
    assert status == STATUS_CRITICAL

def test_determine_overall_status():
    assert determine_overall_status([STATUS_HEALTHY, STATUS_HEALTHY]) == STATUS_HEALTHY
    assert determine_overall_status([STATUS_HEALTHY, STATUS_WARNING]) == STATUS_WARNING
    assert determine_overall_status([STATUS_HEALTHY, STATUS_WARNING, STATUS_CRITICAL]) == STATUS_CRITICAL

def test_evaluate_service_slos():
    sample = {
        "availability_pct": 99.95,
        "success_rate_pct": 99.8,
        "p95_latency_ms": 110.0,
        "error_rate_pct": 0.05
    }
    slos = [
        {"sli_id": "sli-availability", "slo_target": 99.9, "warning_threshold": 99.5, "sla_target": 99.0, "comparison_op": ">="},
        {"sli_id": "sli-response-time", "slo_target": 150.0, "warning_threshold": 250.0, "sla_target": 400.0, "comparison_op": "<="}
    ]

    result = evaluate_service_slos(sample, slos)
    assert result["overall_status"] == STATUS_HEALTHY
    assert len(result["slo_evaluations"]) == 2
    assert result["average_error_budget_pct"] == 38.34

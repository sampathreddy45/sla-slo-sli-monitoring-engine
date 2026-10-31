import pytest
import os
import tempfile
from engine import database, models

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.init_db(path, seed_defaults=True)
    yield path
    try:
        os.remove(path)
    except Exception:
        pass

def test_init_db_and_defaults(temp_db):
    services = models.get_all_services(temp_db)
    assert len(services) >= 4
    service_ids = [s["id"] for s in services]
    assert "svc-checkout" in service_ids
    assert "svc-auth" in service_ids

def test_service_crud(temp_db):
    # Create
    new_svc = {
        "id": "svc-inventory",
        "name": "Warehouse Inventory API",
        "description": "Stock count tracking",
        "tier": "Tier 2",
        "endpoint": "/api/inventory",
        "base_qps": 80
    }
    created = models.create_service(temp_db, new_svc)
    assert created["id"] == "svc-inventory"
    assert created["name"] == "Warehouse Inventory API"

    # Read
    fetched = models.get_service(temp_db, "svc-inventory")
    assert fetched["tier"] == "Tier 2"

    # Update
    updated = models.update_service(temp_db, "svc-inventory", {"tier": "Tier 1", "description": "Updated desc"})
    assert updated["tier"] == "Tier 1"
    assert updated["description"] == "Updated desc"

    # Delete
    deleted = models.delete_service(temp_db, "svc-inventory")
    assert deleted is True
    assert models.get_service(temp_db, "svc-inventory") is None

def test_metrics_insert_and_history(temp_db):
    sample = {
        "service_id": "svc-checkout",
        "total_requests": 500,
        "successful_requests": 498,
        "failed_requests": 2,
        "avg_latency_ms": 42.5,
        "p95_latency_ms": 78.0,
        "p99_latency_ms": 110.0,
        "availability_pct": 99.6,
        "success_rate_pct": 99.6,
        "error_rate_pct": 0.4,
        "status": "HEALTHY"
    }
    sample_id = models.insert_metric_sample(temp_db, sample)
    assert sample_id > 0

    latest = models.get_latest_metric(temp_db, "svc-checkout")
    assert latest is not None
    assert latest["total_requests"] == 500
    assert latest["availability_pct"] == 99.6

    history = models.get_metric_history(temp_db, "svc-checkout", limit=10)
    assert len(history) >= 1
    assert history[-1]["id"] == sample_id

def test_alerts_lifecycle(temp_db):
    alert_id = models.create_alert(temp_db, {
        "service_id": "svc-checkout",
        "sli_id": "sli-availability",
        "severity": "CRITICAL",
        "title": "SLA Breach on Checkout",
        "message": "Availability dipped to 98.2%",
        "current_value": 98.2,
        "threshold_value": 99.0
    })
    assert alert_id > 0

    alerts = models.get_alerts(temp_db, status="ACTIVE")
    assert any(a["id"] == alert_id for a in alerts)

    # Acknowledge
    ack_res = models.acknowledge_alert(temp_db, alert_id)
    assert ack_res is True

    # Resolve
    res_res = models.resolve_alert(temp_db, alert_id)
    assert res_res is True

    resolved_alerts = models.get_alerts(temp_db, status="RESOLVED")
    assert any(a["id"] == alert_id for a in resolved_alerts)

    # Clear resolved
    cleared = models.clear_resolved_alerts(temp_db)
    assert cleared >= 1

def test_simulation_configs(temp_db):
    configs = models.get_simulation_configs(temp_db)
    assert len(configs) >= 4

    models.update_simulation_config(temp_db, "svc-checkout", {
        "mode": "ERROR_FLOOD",
        "error_injection_pct": 25.0
    })

    cfg = models.get_simulation_config(temp_db, "svc-checkout")
    assert cfg["mode"] == "ERROR_FLOOD"
    assert cfg["error_injection_pct"] == 25.0

    models.reset_simulation_configs(temp_db)
    cfg_reset = models.get_simulation_config(temp_db, "svc-checkout")
    assert cfg_reset["mode"] == "NORMAL"
    assert cfg_reset["error_injection_pct"] == 0.0

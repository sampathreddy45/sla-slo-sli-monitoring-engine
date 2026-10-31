import pytest
import os
import tempfile
import json
from engine import create_app
from engine.config import Config

class ApiTestConfig(Config):
    DATABASE = None
    SIMULATOR_ENABLED = False
    TESTING = True

@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    class CustomTestConfig(ApiTestConfig):
        DATABASE = path

    app = create_app(test_config=CustomTestConfig, start_simulator=False)
    # Generate 2 baseline ticks so endpoints have metrics to evaluate
    app.simulator.step_tick()
    app.simulator.step_tick()

    with app.test_client() as client:
        yield client

    try:
        os.remove(path)
    except Exception:
        pass

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_dashboard_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"SLA / SLO / SLI Monitoring Engine" in res.data
    assert b"Chaos Engineering & Traffic Generator" in res.data
    assert b"availabilityChartCanvas" in res.data

def test_api_overview(client):
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert "fleet_availability_pct" in data
    assert "fleet_error_budget_pct" in data
    assert "total_services" in data
    assert data["total_services"] >= 4

def test_api_services(client):
    res = client.get("/api/services")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["services"]) >= 4

    # Single service detail
    res_svc = client.get("/api/services/svc-checkout")
    assert res_svc.status_code == 200
    svc_data = res_svc.get_json()
    assert svc_data["service"]["id"] == "svc-checkout"
    assert "latest_metric" in svc_data

def test_api_create_and_delete_service(client):
    new_svc = {
        "id": "svc-search-test",
        "name": "Search Engine API",
        "tier": "Tier 2",
        "description": "Elastic search gateway",
        "base_qps": 150
    }
    res = client.post("/api/services", json=new_svc)
    assert res.status_code == 201

    # Verify exists
    res_get = client.get("/api/services/svc-search-test")
    assert res_get.status_code == 200

    # Delete
    res_del = client.delete("/api/services/svc-search-test")
    assert res_del.status_code == 200

    # Verify deleted
    res_404 = client.get("/api/services/svc-search-test")
    assert res_404.status_code == 404

def test_api_metrics_history(client):
    res = client.get("/api/services/svc-checkout/metrics?limit=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["service_id"] == "svc-checkout"
    assert "metrics" in data
    assert len(data["metrics"]) >= 1

def test_api_slos_and_update(client):
    res = client.get("/api/services/svc-checkout/slos")
    assert res.status_code == 200
    data = res.get_json()
    slos = data["slos"]
    assert len(slos) >= 1

    first_slo = slos[0]
    slo_id = first_slo["id"]

    # Update SLO threshold
    update_res = client.put(f"/api/services/svc-checkout/slos/{slo_id}", json={
        "slo_target": 99.8,
        "warning_threshold": 99.4,
        "sla_target": 98.9
    })
    assert update_res.status_code == 200

def test_api_simulator_inject_and_reset(client):
    # Inject fault
    inject_res = client.post("/api/simulator/inject", json={
        "service_id": "svc-checkout",
        "scenario": "ERROR_FLOOD",
        "error_injection_pct": 30.0
    })
    assert inject_res.status_code == 200
    data = inject_res.get_json()
    assert data["scenario"] == "ERROR_FLOOD"

    # Reset
    reset_res = client.post("/api/simulator/reset")
    assert reset_res.status_code == 200

def test_api_export_report_csv(client):
    res = client.get("/api/export/report")
    assert res.status_code == 200
    assert "text/csv" in res.content_type
    assert b"Service Name,Tier,SLI Metric" in res.data

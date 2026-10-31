import pytest
import os
import tempfile
from engine import database, models, simulator

@pytest.fixture
def sim_env():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.init_db(path, seed_defaults=True)
    sim = simulator.TrafficSimulator(db_path=path, interval_sec=1.0)
    yield sim, path
    sim.stop()
    try:
        os.remove(path)
    except Exception:
        pass

def test_simulator_single_tick(sim_env):
    sim, db_path = sim_env
    samples = sim.step_tick()
    assert len(samples) >= 4
    for s in samples:
        assert s["total_requests"] > 0
        assert s["availability_pct"] >= 0.0
        assert s["status"] in ("HEALTHY", "WARNING", "CRITICAL")

def test_chaos_latency_spike(sim_env):
    sim, db_path = sim_env
    models.update_simulation_config(db_path, "svc-checkout", {
        "mode": "LATENCY_SPIKE",
        "added_latency_ms": 1000.0
    })

    samples = sim.step_tick()
    checkout_sample = next(s for s in samples if s["service_id"] == "svc-checkout")
    assert checkout_sample["avg_latency_ms"] > 800.0

def test_chaos_total_outage_triggers_critical_alert(sim_env):
    sim, db_path = sim_env
    # Inject total outage
    models.update_simulation_config(db_path, "svc-checkout", {
        "mode": "TOTAL_OUTAGE"
    })

    samples = sim.step_tick()
    checkout_sample = next(s for s in samples if s["service_id"] == "svc-checkout")
    assert checkout_sample["availability_pct"] <= 5.0
    assert checkout_sample["status"] == "CRITICAL"

    # Verify critical alert was generated in database
    alerts = models.get_alerts(db_path, status="ACTIVE")
    checkout_alerts = [a for a in alerts if a["service_id"] == "svc-checkout" and a["severity"] == "CRITICAL"]
    assert len(checkout_alerts) >= 1

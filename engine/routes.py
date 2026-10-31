import time
import csv
import io
from flask import Blueprint, current_app, request, jsonify, render_template, Response
from engine import models
from engine import evaluator

api_bp = Blueprint("api", __name__)

def get_db_path() -> str:
    return current_app.config["DATABASE"]

def get_simulator():
    return getattr(current_app, "simulator", None)

@api_bp.route("/")
def index():
    """Serve the monitoring dashboard UI."""
    return render_template("index.html")

@api_bp.route("/api/health")
def health():
    """System health status."""
    sim = get_simulator()
    is_running = sim.is_running() if sim else False
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "simulator_active": is_running
    })

@api_bp.route("/api/overview")
def overview():
    """Fleet-wide high-level SLA/SLO metrics and active alert counts."""
    db_path = get_db_path()
    services = models.get_all_services(db_path)
    active_alerts = models.get_alerts(db_path, status="ACTIVE", limit=100)

    total_services = len(services)
    status_counts = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0}
    
    total_qps = 0
    availability_sum = 0.0
    error_budget_sum = 0.0
    evaluated_services = 0

    services_summary = []

    for svc in services:
        svc_id = svc["id"]
        latest_metric = models.get_latest_metric(db_path, svc_id)
        slos = models.get_service_slos(db_path, svc_id)
        
        if latest_metric and slos:
            eval_result = evaluator.evaluate_service_slos(latest_metric, slos)
            status = eval_result["overall_status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            
            availability_sum += latest_metric.get("availability_pct", 100.0)
            error_budget_sum += eval_result.get("average_error_budget_pct", 100.0)
            total_qps += int(latest_metric.get("total_requests", 0) / 2) # approx per second
            evaluated_services += 1
            
            services_summary.append({
                "id": svc_id,
                "name": svc["name"],
                "tier": svc["tier"],
                "status": status,
                "availability": latest_metric.get("availability_pct", 100.0),
                "latency_p95": latest_metric.get("p95_latency_ms", 0.0),
                "error_rate": latest_metric.get("error_rate_pct", 0.0),
                "error_budget_remaining": eval_result.get("average_error_budget_pct", 100.0)
            })
        else:
            status_counts["HEALTHY"] += 1

    fleet_availability = round(availability_sum / max(1, evaluated_services), 3) if evaluated_services > 0 else 100.0
    fleet_error_budget = round(error_budget_sum / max(1, evaluated_services), 2) if evaluated_services > 0 else 100.0

    critical_alerts = [a for a in active_alerts if a["severity"] == "CRITICAL"]
    warning_alerts = [a for a in active_alerts if a["severity"] == "WARNING"]

    sim = get_simulator()

    return jsonify({
        "timestamp": time.time(),
        "total_services": total_services,
        "status_counts": status_counts,
        "fleet_availability_pct": fleet_availability,
        "fleet_error_budget_pct": fleet_error_budget,
        "fleet_qps": total_qps,
        "active_alerts_count": len(active_alerts),
        "critical_alerts_count": len(critical_alerts),
        "warning_alerts_count": len(warning_alerts),
        "simulator_running": sim.is_running() if sim else False,
        "services": services_summary
    })

@api_bp.route("/api/services", methods=["GET"])
def list_services():
    """List all monitored services with latest metric & evaluated status."""
    db_path = get_db_path()
    services = models.get_all_services(db_path)
    result = []

    for svc in services:
        svc_id = svc["id"]
        latest_metric = models.get_latest_metric(db_path, svc_id)
        slos = models.get_service_slos(db_path, svc_id)
        sim_cfg = models.get_simulation_config(db_path, svc_id)

        eval_result = {"overall_status": "HEALTHY", "average_error_budget_pct": 100.0, "slo_evaluations": []}
        if latest_metric and slos:
            eval_result = evaluator.evaluate_service_slos(latest_metric, slos)

        result.append({
            "service": svc,
            "latest_metric": latest_metric,
            "overall_status": eval_result["overall_status"],
            "average_error_budget_pct": eval_result["average_error_budget_pct"],
            "slo_evaluations": eval_result["slo_evaluations"],
            "simulation_config": sim_cfg
        })

    return jsonify({"services": result})

@api_bp.route("/api/services/<service_id>", methods=["GET"])
def get_service_detail(service_id):
    """Retrieve detailed service data."""
    db_path = get_db_path()
    svc = models.get_service(db_path, service_id)
    if not svc:
        return jsonify({"error": "Service not found"}), 404

    latest_metric = models.get_latest_metric(db_path, service_id)
    slos = models.get_service_slos(db_path, service_id)
    sim_cfg = models.get_simulation_config(db_path, service_id)

    eval_result = {"overall_status": "HEALTHY", "average_error_budget_pct": 100.0, "slo_evaluations": []}
    if latest_metric and slos:
        eval_result = evaluator.evaluate_service_slos(latest_metric, slos)

    return jsonify({
        "service": svc,
        "latest_metric": latest_metric,
        "overall_status": eval_result["overall_status"],
        "average_error_budget_pct": eval_result["average_error_budget_pct"],
        "slo_evaluations": eval_result["slo_evaluations"],
        "simulation_config": sim_cfg
    })

@api_bp.route("/api/services", methods=["POST"])
def add_service():
    """Register a new service to monitor."""
    data = request.get_json() or {}
    if not data.get("id") or not data.get("name"):
        return jsonify({"error": "Missing required fields 'id' and 'name'"}), 400

    db_path = get_db_path()
    if models.get_service(db_path, data["id"]):
        return jsonify({"error": "Service with this ID already exists"}), 409

    svc = models.create_service(db_path, data)
    return jsonify({"message": "Service created successfully", "service": svc}), 201

@api_bp.route("/api/services/<service_id>", methods=["PUT"])
def update_service_info(service_id):
    """Update service metadata."""
    data = request.get_json() or {}
    db_path = get_db_path()
    svc = models.get_service(db_path, service_id)
    if not svc:
        return jsonify({"error": "Service not found"}), 404

    updated = models.update_service(db_path, service_id, data)
    return jsonify({"message": "Service updated", "service": updated})

@api_bp.route("/api/services/<service_id>", methods=["DELETE"])
def delete_service(service_id):
    """Delete a service."""
    db_path = get_db_path()
    success = models.delete_service(db_path, service_id)
    if not success:
        return jsonify({"error": "Service not found"}), 404
    return jsonify({"message": f"Service '{service_id}' deleted successfully"})

@api_bp.route("/api/services/<service_id>/metrics")
def get_service_metrics(service_id):
    """Retrieve historical time-series metric samples for charts."""
    db_path = get_db_path()
    limit = int(request.args.get("limit", 60))
    history = models.get_metric_history(db_path, service_id, limit=limit)
    return jsonify({
        "service_id": service_id,
        "count": len(history),
        "metrics": history
    })

@api_bp.route("/api/services/<service_id>/slos")
def get_service_slos(service_id):
    """Get SLO configurations for a service."""
    db_path = get_db_path()
    slos = models.get_service_slos(db_path, service_id)
    return jsonify({"service_id": service_id, "slos": slos})

@api_bp.route("/api/services/<service_id>/slos/<int:slo_id>", methods=["PUT"])
def update_slo(service_id, slo_id):
    """Update thresholds for a specific SLO."""
    data = request.get_json() or {}
    db_path = get_db_path()
    success = models.update_service_slo(db_path, slo_id, data)
    if not success:
        return jsonify({"error": "SLO target not found"}), 404
    return jsonify({"message": "SLO thresholds updated successfully"})

@api_bp.route("/api/alerts")
def list_alerts():
    """Retrieve alert events."""
    db_path = get_db_path()
    status = request.args.get("status")
    limit = int(request.args.get("limit", 50))
    alerts = models.get_alerts(db_path, status=status, limit=limit)
    return jsonify({
        "count": len(alerts),
        "alerts": alerts
    })

@api_bp.route("/api/alerts/<int:alert_id>/ack", methods=["POST"])
def ack_alert(alert_id):
    """Acknowledge an alert."""
    db_path = get_db_path()
    success = models.acknowledge_alert(db_path, alert_id)
    if not success:
        return jsonify({"error": "Alert not found or already acknowledged"}), 404
    return jsonify({"message": f"Alert {alert_id} acknowledged"})

@api_bp.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert_route(alert_id):
    """Manually mark an alert as resolved."""
    db_path = get_db_path()
    success = models.resolve_alert(db_path, alert_id)
    if not success:
        return jsonify({"error": "Alert not found or already resolved"}), 404
    return jsonify({"message": f"Alert {alert_id} resolved"})

@api_bp.route("/api/alerts/clear-resolved", methods=["POST"])
def clear_resolved_alerts_route():
    """Delete all resolved alerts."""
    db_path = get_db_path()
    count = models.clear_resolved_alerts(db_path)
    return jsonify({"message": f"Cleared {count} resolved alerts"})

@api_bp.route("/api/simulator/status")
def simulator_status():
    """Get simulation settings across services."""
    db_path = get_db_path()
    sim = get_simulator()
    configs = models.get_simulation_configs(db_path)
    return jsonify({
        "is_running": sim.is_running() if sim else False,
        "is_paused": sim.paused if sim else True,
        "tick_count": sim.tick_count if sim else 0,
        "configs": configs
    })

@api_bp.route("/api/simulator/inject", methods=["POST"])
def inject_fault():
    """
    Inject chaos failure scenario or adjust traffic:
    Body:
    {
        "service_id": "svc-checkout" | "all",
        "scenario": "NORMAL" | "TRAFFIC_SPIKE" | "LATENCY_SPIKE" | "ERROR_FLOOD" | "PARTIAL_OUTAGE" | "TOTAL_OUTAGE" | "FLAPPING",
        "added_latency_ms": 0,
        "error_injection_pct": 0,
        "base_qps": 100
    }
    """
    data = request.get_json() or {}
    service_id = data.get("service_id", "all")
    scenario = data.get("scenario", "NORMAL").upper()
    db_path = get_db_path()

    valid_scenarios = ["NORMAL", "TRAFFIC_SPIKE", "LATENCY_SPIKE", "ERROR_FLOOD", "PARTIAL_OUTAGE", "TOTAL_OUTAGE", "FLAPPING"]
    if scenario not in valid_scenarios:
        return jsonify({"error": f"Invalid scenario. Allowed: {valid_scenarios}"}), 400

    target_services = []
    if service_id == "all":
        target_services = [s["id"] for s in models.get_all_services(db_path)]
    else:
        target_services = [service_id]

    updated_count = 0
    for sid in target_services:
        updates = {"mode": scenario}
        if "added_latency_ms" in data:
            updates["added_latency_ms"] = float(data["added_latency_ms"])
        if "error_injection_pct" in data:
            updates["error_injection_pct"] = float(data["error_injection_pct"])
        if "base_qps" in data:
            updates["base_qps"] = int(data["base_qps"])

        # Reset injected errors/latency when explicitly returning to NORMAL
        if scenario == "NORMAL" and "error_injection_pct" not in data and "added_latency_ms" not in data:
            updates["error_injection_pct"] = 0.0
            updates["added_latency_ms"] = 0.0

        if models.update_simulation_config(db_path, sid, updates):
            updated_count += 1

    # Trigger immediate step tick so user sees the effect immediately
    sim = get_simulator()
    if sim:
        sim.step_tick()

    return jsonify({
        "message": f"Injected '{scenario}' scenario into {updated_count} service(s)",
        "scenario": scenario,
        "target_services": target_services
    })

@api_bp.route("/api/simulator/reset", methods=["POST"])
def reset_simulation():
    """Reset all simulation states back to NORMAL healthy state."""
    db_path = get_db_path()
    models.reset_simulation_configs(db_path)
    sim = get_simulator()
    if sim:
        sim.step_tick()
    return jsonify({"message": "All services reset to NORMAL healthy operation"})

@api_bp.route("/api/simulator/toggle", methods=["POST"])
def toggle_simulator():
    """Toggle simulator pause/resume."""
    sim = get_simulator()
    if not sim:
        return jsonify({"error": "Simulator not initialized"}), 500

    if sim.paused:
        sim.resume()
        state = "resumed"
    else:
        sim.pause()
        state = "paused"

    return jsonify({"message": f"Simulator {state}", "is_running": sim.is_running()})

@api_bp.route("/api/simulator/tick", methods=["POST"])
def manual_tick():
    """Perform a single manual simulation step."""
    sim = get_simulator()
    if not sim:
        return jsonify({"error": "Simulator not initialized"}), 500

    samples = sim.step_tick()
    return jsonify({
        "message": f"Generated tick {sim.tick_count}",
        "samples_count": len(samples)
    })

@api_bp.route("/api/export/report")
def export_report():
    """Export SLA compliance report as CSV."""
    db_path = get_db_path()
    services = models.get_all_services(db_path)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp",
        "Service ID",
        "Service Name",
        "Tier",
        "SLI Metric",
        "Current Value",
        "SLO Target",
        "SLA Target",
        "Status",
        "Remaining Error Budget (%)",
        "Compliance"
    ])

    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    for svc in services:
        svc_id = svc["id"]
        latest_metric = models.get_latest_metric(db_path, svc_id)
        slos = models.get_service_slos(db_path, svc_id)
        if latest_metric and slos:
            eval_result = evaluator.evaluate_service_slos(latest_metric, slos)
            for item in eval_result["slo_evaluations"]:
                compliant = "YES" if item["status"] != "CRITICAL" else "BREACHED"
                writer.writerow([
                    now_str,
                    svc_id,
                    svc["name"],
                    svc["tier"],
                    item["sli_name"],
                    f"{item['current_value']:.2f}{item['unit']}",
                    f"{item['slo_target']:.2f}{item['unit']}",
                    f"{item['sla_target']:.2f}{item['unit']}",
                    item["status"],
                    f"{item['error_budget']['budget_remaining_pct']:.1f}%",
                    compliant
                ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sla_compliance_report.csv"}
    )

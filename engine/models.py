import time
from typing import List, Dict, Any, Optional
from engine.database import get_db_context

def row_to_dict(row) -> Dict[str, Any]:
    """Convert sqlite3.Row to standard dictionary."""
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}

def get_all_services(db_path: str) -> List[Dict[str, Any]]:
    """Retrieve all monitored services."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("SELECT * FROM services ORDER BY tier ASC, name ASC")
        return [row_to_dict(r) for r in cursor.fetchall()]

def get_service(db_path: str, service_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve single service by ID."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None

def create_service(db_path: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new service with default simulation configuration."""
    with get_db_context(db_path) as conn:
        conn.execute(
            """
            INSERT INTO services (id, name, description, tier, endpoint)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                service_data["id"],
                service_data["name"],
                service_data.get("description", ""),
                service_data.get("tier", "Tier 2"),
                service_data.get("endpoint", f"/api/{service_data['id']}")
            )
        )
        conn.execute(
            """
            INSERT INTO simulation_configs (service_id, mode, base_qps, error_injection_pct, added_latency_ms, updated_at)
            VALUES (?, 'NORMAL', ?, 0.0, 0.0, ?)
            """,
            (service_data["id"], service_data.get("base_qps", 100), time.time())
        )
    return get_service(db_path, service_data["id"])

def update_service(db_path: str, service_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update existing service metadata."""
    with get_db_context(db_path) as conn:
        conn.execute(
            """
            UPDATE services
            SET name = COALESCE(?, name),
                description = COALESCE(?, description),
                tier = COALESCE(?, tier),
                endpoint = COALESCE(?, endpoint)
            WHERE id = ?
            """,
            (
                updates.get("name"),
                updates.get("description"),
                updates.get("tier"),
                updates.get("endpoint"),
                service_id
            )
        )
    return get_service(db_path, service_id)

def delete_service(db_path: str, service_id: str) -> bool:
    """Delete service and cascading metrics/alerts."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
        return cursor.rowcount > 0

def get_service_slos(db_path: str, service_id: str) -> List[Dict[str, Any]]:
    """Retrieve all SLO configurations for a given service."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT s.*, sli.name as sli_name, sli.metric_key, sli.unit, sli.description as sli_description
            FROM slo_targets s
            JOIN sli_definitions sli ON s.sli_id = sli.id
            WHERE s.service_id = ?
            ORDER BY sli.name ASC
            """,
            (service_id,)
        )
        return [row_to_dict(r) for r in cursor.fetchall()]

def update_service_slo(db_path: str, slo_id: int, updates: Dict[str, Any]) -> bool:
    """Update SLO thresholds."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE slo_targets
            SET slo_target = COALESCE(?, slo_target),
                warning_threshold = COALESCE(?, warning_threshold),
                sla_target = COALESCE(?, sla_target),
                comparison_op = COALESCE(?, comparison_op)
            WHERE id = ?
            """,
            (
                updates.get("slo_target"),
                updates.get("warning_threshold"),
                updates.get("sla_target"),
                updates.get("comparison_op"),
                slo_id
            )
        )
        return cursor.rowcount > 0

def insert_metric_sample(db_path: str, sample: Dict[str, Any]) -> int:
    """Insert time-series sample for a service."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO metric_samples (
                timestamp, service_id, total_requests, successful_requests, failed_requests,
                avg_latency_ms, p95_latency_ms, p99_latency_ms, availability_pct,
                success_rate_pct, error_rate_pct, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample.get("timestamp", time.time()),
                sample["service_id"],
                sample.get("total_requests", 0),
                sample.get("successful_requests", 0),
                sample.get("failed_requests", 0),
                sample.get("avg_latency_ms", 0.0),
                sample.get("p95_latency_ms", 0.0),
                sample.get("p99_latency_ms", 0.0),
                sample.get("availability_pct", 100.0),
                sample.get("success_rate_pct", 100.0),
                sample.get("error_rate_pct", 0.0),
                sample.get("status", "HEALTHY")
            )
        )
        return cursor.lastrowid

def get_latest_metric(db_path: str, service_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve most recent metric sample for a service."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM metric_samples
            WHERE service_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (service_id,)
        )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None

def get_metric_history(db_path: str, service_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent time-series metric samples for charts, in chronological order."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM (
                SELECT * FROM metric_samples
                WHERE service_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
            """,
            (service_id, limit)
        )
        return [row_to_dict(r) for r in cursor.fetchall()]

def prune_old_metrics(db_path: str, max_samples_per_service: int = 500):
    """Keep table compact by removing metrics exceeding retention limit."""
    with get_db_context(db_path) as conn:
        services = conn.execute("SELECT id FROM services").fetchall()
        for svc in services:
            svc_id = svc["id"]
            conn.execute(
                """
                DELETE FROM metric_samples
                WHERE service_id = ? AND id NOT IN (
                    SELECT id FROM metric_samples
                    WHERE service_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                """,
                (svc_id, svc_id, max_samples_per_service)
            )

def get_alerts(db_path: str, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve alerts ordered by timestamp descending."""
    with get_db_context(db_path) as conn:
        if status:
            cursor = conn.execute(
                """
                SELECT a.*, s.name as service_name
                FROM alerts a
                JOIN services s ON a.service_id = s.id
                WHERE a.status = ?
                ORDER BY a.created_at DESC
                LIMIT ?
                """,
                (status.upper(), limit)
            )
        else:
            cursor = conn.execute(
                """
                SELECT a.*, s.name as service_name
                FROM alerts a
                JOIN services s ON a.service_id = s.id
                ORDER BY a.created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
        return [row_to_dict(r) for r in cursor.fetchall()]

def get_active_alert_for_sli(db_path: str, service_id: str, sli_id: str) -> Optional[Dict[str, Any]]:
    """Check if there is already an active alert for this service & SLI."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM alerts
            WHERE service_id = ? AND sli_id = ? AND status IN ('ACTIVE', 'ACKNOWLEDGED')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (service_id, sli_id)
        )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None

def create_alert(db_path: str, alert_data: Dict[str, Any]) -> int:
    """Record a new alert notification."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO alerts (
                service_id, sli_id, severity, title, message, current_value, threshold_value,
                status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (
                alert_data["service_id"],
                alert_data["sli_id"],
                alert_data["severity"],
                alert_data["title"],
                alert_data["message"],
                alert_data["current_value"],
                alert_data["threshold_value"],
                alert_data.get("created_at", time.time())
            )
        )
        return cursor.lastrowid

def acknowledge_alert(db_path: str, alert_id: int) -> bool:
    """Mark an alert as acknowledged by on-call engineer."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            "UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE id = ? AND status = 'ACTIVE'",
            (alert_id,)
        )
        return cursor.rowcount > 0

def resolve_alert(db_path: str, alert_id: int) -> bool:
    """Manually resolve an alert."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            "UPDATE alerts SET status = 'RESOLVED', resolved_at = ? WHERE id = ? AND status != 'RESOLVED'",
            (time.time(), alert_id)
        )
        return cursor.rowcount > 0

def resolve_alerts_for_sli(db_path: str, service_id: str, sli_id: str):
    """Auto-resolve active alerts when metric recovers to Healthy."""
    with get_db_context(db_path) as conn:
        conn.execute(
            """
            UPDATE alerts
            SET status = 'RESOLVED', resolved_at = ?
            WHERE service_id = ? AND sli_id = ? AND status IN ('ACTIVE', 'ACKNOWLEDGED')
            """,
            (time.time(), service_id, sli_id)
        )

def clear_resolved_alerts(db_path: str) -> int:
    """Delete resolved alerts to tidy dashboard."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("DELETE FROM alerts WHERE status = 'RESOLVED'")
        return cursor.rowcount

def get_simulation_configs(db_path: str) -> List[Dict[str, Any]]:
    """Get simulation configs for all services."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("SELECT * FROM simulation_configs")
        return [row_to_dict(r) for r in cursor.fetchall()]

def get_simulation_config(db_path: str, service_id: str) -> Optional[Dict[str, Any]]:
    """Get simulation config for a specific service."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute("SELECT * FROM simulation_configs WHERE service_id = ?", (service_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None

def update_simulation_config(db_path: str, service_id: str, updates: Dict[str, Any]) -> bool:
    """Update simulation parameters for a service."""
    with get_db_context(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE simulation_configs
            SET mode = COALESCE(?, mode),
                base_qps = COALESCE(?, base_qps),
                error_injection_pct = COALESCE(?, error_injection_pct),
                added_latency_ms = COALESCE(?, added_latency_ms),
                updated_at = ?
            WHERE service_id = ?
            """,
            (
                updates.get("mode"),
                updates.get("base_qps"),
                updates.get("error_injection_pct"),
                updates.get("added_latency_ms"),
                time.time(),
                service_id
            )
        )
        return cursor.rowcount > 0

def reset_simulation_configs(db_path: str):
    """Reset all services back to NORMAL healthy state."""
    with get_db_context(db_path) as conn:
        conn.execute(
            """
            UPDATE simulation_configs
            SET mode = 'NORMAL',
                error_injection_pct = 0.0,
                added_latency_ms = 0.0,
                updated_at = ?
            """,
            (time.time(),)
        )

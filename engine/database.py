import sqlite3
import os
import time
from contextlib import contextmanager

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    tier TEXT NOT NULL DEFAULT 'Tier 1',
    endpoint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sli_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    metric_key TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS slo_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id TEXT NOT NULL,
    sli_id TEXT NOT NULL,
    slo_target REAL NOT NULL,
    warning_threshold REAL NOT NULL,
    sla_target REAL NOT NULL,
    comparison_op TEXT NOT NULL DEFAULT '>=',
    window_duration TEXT NOT NULL DEFAULT 'rolling_1h',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY(sli_id) REFERENCES sli_definitions(id) ON DELETE CASCADE,
    UNIQUE(service_id, sli_id)
);

CREATE TABLE IF NOT EXISTS metric_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    service_id TEXT NOT NULL,
    total_requests INTEGER NOT NULL DEFAULT 0,
    successful_requests INTEGER NOT NULL DEFAULT 0,
    failed_requests INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms REAL NOT NULL DEFAULT 0.0,
    p95_latency_ms REAL NOT NULL DEFAULT 0.0,
    p99_latency_ms REAL NOT NULL DEFAULT 0.0,
    availability_pct REAL NOT NULL DEFAULT 100.0,
    success_rate_pct REAL NOT NULL DEFAULT 100.0,
    error_rate_pct REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'HEALTHY',
    FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metric_samples_service_time 
ON metric_samples(service_id, timestamp);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id TEXT NOT NULL,
    sli_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    current_value REAL NOT NULL,
    threshold_value REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL,
    resolved_at REAL,
    FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alerts_service_status 
ON alerts(service_id, status);

CREATE TABLE IF NOT EXISTS simulation_configs (
    service_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL DEFAULT 'NORMAL',
    base_qps INTEGER NOT NULL DEFAULT 100,
    error_injection_pct REAL NOT NULL DEFAULT 0.0,
    added_latency_ms REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL,
    FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
);
"""

DEFAULT_SLIS = [
    ("sli-availability", "Availability", "availability", "%", "Percentage of requests successfully handled without 5xx errors"),
    ("sli-success-rate", "Request Success Rate", "success_rate", "%", "Percentage of requests returning HTTP 2xx or 3xx"),
    ("sli-response-time", "Response Time (P95)", "response_time", "ms", "95th percentile latency in milliseconds"),
    ("sli-error-rate", "Error Rate", "error_rate", "%", "Percentage of total requests resulting in failures (4xx/5xx)"),
]

DEFAULT_SERVICES = [
    {
        "id": "svc-checkout",
        "name": "Checkout & Payment Gateway",
        "description": "Processes customer credit cards, digital wallets, and checkout transactions.",
        "tier": "Tier 1 - Mission Critical",
        "endpoint": "/api/v1/checkout",
        "base_qps": 220,
        "slos": [
            {"sli_id": "sli-availability", "slo_target": 99.9, "warning_threshold": 99.5, "sla_target": 99.0, "comparison_op": ">="},
            {"sli_id": "sli-success-rate", "slo_target": 99.5, "warning_threshold": 99.0, "sla_target": 98.0, "comparison_op": ">="},
            {"sli_id": "sli-response-time", "slo_target": 180.0, "warning_threshold": 300.0, "sla_target": 500.0, "comparison_op": "<="},
            {"sli_id": "sli-error-rate", "slo_target": 0.5, "warning_threshold": 1.5, "sla_target": 3.0, "comparison_op": "<="},
        ]
    },
    {
        "id": "svc-auth",
        "name": "User Auth & Identity API",
        "description": "Handles OAuth2 tokens, session validation, SSO, and user logins.",
        "tier": "Tier 1 - Mission Critical",
        "endpoint": "/api/v1/auth",
        "base_qps": 350,
        "slos": [
            {"sli_id": "sli-availability", "slo_target": 99.95, "warning_threshold": 99.7, "sla_target": 99.2, "comparison_op": ">="},
            {"sli_id": "sli-success-rate", "slo_target": 99.7, "warning_threshold": 99.2, "sla_target": 98.5, "comparison_op": ">="},
            {"sli_id": "sli-response-time", "slo_target": 120.0, "warning_threshold": 250.0, "sla_target": 400.0, "comparison_op": "<="},
            {"sli_id": "sli-error-rate", "slo_target": 0.3, "warning_threshold": 1.0, "sla_target": 2.5, "comparison_op": "<="},
        ]
    },
    {
        "id": "svc-catalog",
        "name": "Product Catalog & Search",
        "description": "Elasticsearch backed inventory catalog, search queries, and product details.",
        "tier": "Tier 2 - Business Essential",
        "endpoint": "/api/v1/products",
        "base_qps": 180,
        "slos": [
            {"sli_id": "sli-availability", "slo_target": 99.5, "warning_threshold": 99.0, "sla_target": 98.0, "comparison_op": ">="},
            {"sli_id": "sli-success-rate", "slo_target": 99.0, "warning_threshold": 98.0, "sla_target": 97.0, "comparison_op": ">="},
            {"sli_id": "sli-response-time", "slo_target": 250.0, "warning_threshold": 450.0, "sla_target": 700.0, "comparison_op": "<="},
            {"sli_id": "sli-error-rate", "slo_target": 1.0, "warning_threshold": 2.0, "sla_target": 4.0, "comparison_op": "<="},
        ]
    },
    {
        "id": "svc-notifications",
        "name": "Notification & Email Delivery",
        "description": "Asynchronous push notification and transactional email dispatcher.",
        "tier": "Tier 3 - Standard Support",
        "endpoint": "/api/v1/notify",
        "base_qps": 90,
        "slos": [
            {"sli_id": "sli-availability", "slo_target": 99.0, "warning_threshold": 98.0, "sla_target": 97.0, "comparison_op": ">="},
            {"sli_id": "sli-success-rate", "slo_target": 98.5, "warning_threshold": 97.5, "sla_target": 96.0, "comparison_op": ">="},
            {"sli_id": "sli-response-time", "slo_target": 400.0, "warning_threshold": 650.0, "sla_target": 1000.0, "comparison_op": "<="},
            {"sli_id": "sli-error-rate", "slo_target": 1.5, "warning_threshold": 3.0, "sla_target": 5.0, "comparison_op": "<="},
        ]
    }
]

def get_connection(db_path: str):
    """Create a new SQLite connection with foreign keys and dict rows."""
    conn = sqlite3.connect(db_path, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db_context(db_path: str):
    """Context manager for safe database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str, seed_defaults: bool = True):
    """Initialize SQLite database tables and seed baseline data."""
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    with get_db_context(db_path) as conn:
        conn.executescript(SCHEMA_SQL)

        if seed_defaults:
            # Seed SLI definitions
            for sli in DEFAULT_SLIS:
                conn.execute(
                    """
                    INSERT INTO sli_definitions (id, name, metric_key, unit, description)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        metric_key=excluded.metric_key,
                        unit=excluded.unit,
                        description=excluded.description;
                    """,
                    sli
                )

            # Seed default services, SLOs, and simulation configs
            for svc in DEFAULT_SERVICES:
                conn.execute(
                    """
                    INSERT INTO services (id, name, description, tier, endpoint)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        tier=excluded.tier,
                        endpoint=excluded.endpoint;
                    """,
                    (svc["id"], svc["name"], svc["description"], svc["tier"], svc["endpoint"])
                )

                conn.execute(
                    """
                    INSERT INTO simulation_configs (service_id, mode, base_qps, error_injection_pct, added_latency_ms, updated_at)
                    VALUES (?, 'NORMAL', ?, 0.0, 0.0, ?)
                    ON CONFLICT(service_id) DO NOTHING;
                    """,
                    (svc["id"], svc["base_qps"], time.time())
                )

                for slo in svc["slos"]:
                    conn.execute(
                        """
                        INSERT INTO slo_targets (service_id, sli_id, slo_target, warning_threshold, sla_target, comparison_op)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(service_id, sli_id) DO UPDATE SET
                            slo_target=excluded.slo_target,
                            warning_threshold=excluded.warning_threshold,
                            sla_target=excluded.sla_target,
                            comparison_op=excluded.comparison_op;
                        """,
                        (svc["id"], slo["sli_id"], slo["slo_target"], slo["warning_threshold"], slo["sla_target"], slo["comparison_op"])
                    )

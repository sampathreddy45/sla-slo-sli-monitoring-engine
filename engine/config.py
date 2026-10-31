import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DB_PATH = os.path.join(BASE_DIR, "sla_monitor.db")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "sla-slo-sli-secret-key-2026")
    DATABASE = os.environ.get("DATABASE_PATH", DB_PATH)
    SIMULATOR_ENABLED = os.environ.get("SIMULATOR_ENABLED", "true").lower() == "true"
    SIMULATOR_INTERVAL_SEC = float(os.environ.get("SIMULATOR_INTERVAL_SEC", 2.0))
    METRIC_RETENTION_MAX_SAMPLES = int(os.environ.get("METRIC_RETENTION_MAX_SAMPLES", 1000))

class TestConfig(Config):
    DATABASE = ":memory:"
    SIMULATOR_ENABLED = False
    TESTING = True

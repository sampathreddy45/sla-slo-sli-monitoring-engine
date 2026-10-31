# ⚡ SLA, SLO & SLI Monitoring Engine

A production-grade **Site Reliability Engineering (SRE) Observability & Chaos Control Platform** built from scratch with **Python Flask**, **SQLite**, **vanilla JavaScript**, and **Chart.js**.

Designed for engineers, DevOps teams, and beginners to learn, monitor, and test real-time **Service Level Agreements (SLA)**, **Service Level Objectives (SLO)**, **Service Level Indicators (SLI)**, and **Error Budgets**.

---

## 📖 Key Concepts Explained (SRE Fundamentals)

| Term | Full Name | Definition | Example in Engine |
| :--- | :--- | :--- | :--- |
| **SLI** | **Service Level Indicator** | A quantifiable metric measuring how well a service is performing in real time. | *Availability (99.95%)*, *Request Success Rate (99.8%)*, *P95 Latency (120ms)*, *Error Rate (0.05%)* |
| **SLO** | **Service Level Objective** | An internal target agreed upon by the engineering team to ensure system reliability. | *Target availability ≥ 99.9% over a rolling window* |
| **SLA** | **Service Level Agreement** | A formal commitment to customers or stakeholders. Breaching an SLA results in penalties or refunds. | *Availability must never drop below 99.0%* |
| **Error Budget** | **Allowable Unreliability** | The room for failure before violating the SLO (`100% - SLO%`). When budget reaches 0%, releases are frozen. | *If SLO is 99.9%, you have an error budget of 0.1%* |
| **Burn Rate** | **Budget Consumption Speed** | How quickly your error budget is being consumed relative to normal operation (`> 1.0x` means at risk). | *A 500 error flood causing 25% errors burns budget at 50x rate* |

### Health Status Levels
- 🟢 **HEALTHY**: Performance meets or exceeds all internal SLO targets.
- 🟡 **WARNING**: Metric degraded below SLO, but still within legal SLA commitment. Error budget is actively burning.
- 🔴 **CRITICAL**: SLA breached or service experiencing an outage. Instant critical alert raised for on-call engineers.

---

## 🌟 Key Features

1. **Real-Time Monitoring Cockpit**:
   - Sleek SRE dark/light observability UI with live animated status indicators.
   - Real-time fleet KPI summary: Fleet Availability %, Remaining Error Budget %, Active Incidents, and Live QPS.
2. **Interactive Time-Series Charts (Chart.js)**:
   - **Availability & Success Rate (%)** with target SLO lines.
   - **Response Time Latencies (Avg, P95, P99 ms)**.
   - **HTTP Error Rate (%)**.
   - **Remaining Error Budget Headroom (%)**.
3. **Chaos Engineering & Traffic Generator**:
   - Built-in traffic simulator continuously generating realistic microservice requests.
   - Interactive failure injection buttons:
     - 🟢 **Normal Traffic** (Baseline 99.9% health)
     - 📈 **Traffic Surge** (6x spike simulating flash sales)
     - 🐌 **Database Lag** (Injects +750ms latency degradation)
     - 💥 **500 Error Flood** (Simulates 25% backend application crashes)
     - ⚠️ **Partial Outage** (50% failure rate)
     - 🚨 **Total Service Outage** (100% downtime, immediate SLA breach)
     - ⚡ **Intermittent Flapping** (Oscillating stability)
4. **Automated Alerting Engine**:
   - Generates notifications when thresholds enter Warning or Critical states.
   - Automatic alert resolution when metrics return to Healthy.
   - Interactive triage: on-call engineers can **Acknowledge (Ack)** or **Resolve** incidents.
   - Optional browser audio alert chime (Web Audio API).
5. **SLA Audit Reporting**:
   - 1-click export of downloadable CSV compliance reports for audit reviews.
6. **Persistence & Portability**:
   - SQLite database with write-ahead logging (WAL) and automatic metric retention pruning.
   - Docker and Docker Compose support.
   - GitHub Actions CI/CD pipeline.
   - 26 comprehensive automated tests using `pytest`.

---

## 🏗️ Project Architecture

```
SLA-Monitoring-Engine/
├── engine/
│   ├── __init__.py           # Flask app factory, simulator lifecycle
│   ├── config.py             # Environment configurations
│   ├── database.py           # SQLite connection manager, schemas & seed data
│   ├── models.py             # Database CRUD for Services, SLIs, Metrics, Alerts
│   ├── evaluator.py          # Math engine for SLIs, SLOs, SLAs & Error Budgets
│   ├── simulator.py          # Traffic generator & chaos fault injection engine
│   └── routes.py             # REST API endpoints & dashboard controller
├── static/
│   ├── css/style.css         # Modern SRE high-contrast dark/light theme
│   └── js/
│       ├── api.js            # REST API client
│       ├── charts.js         # Chart.js initialization & dynamic time-series
│       ├── simulator.js      # Chaos control handlers & sliders
│       └── dashboard.js      # Real-time state management & polling loop
├── templates/
│   └── index.html            # Single-page dashboard application
├── tests/
│   ├── test_evaluator.py     # SLI/SLO math and error budget unit tests
│   ├── test_models.py        # Database operations & data integrity tests
│   ├── test_simulator.py     # Traffic & chaos fault injection tests
│   └── test_api.py           # Flask REST API integration tests
├── .github/workflows/ci.yml  # GitHub Actions automated test & build pipeline
├── Dockerfile                # Multi-platform container configuration
├── docker-compose.yml        # Orchestration with persistent storage volume
├── pytest.ini                # Pytest configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application CLI entry point
└── README.md                 # Documentation
```

---

## 🚀 Quick Start (Beginner Friendly)

### Option 1: Run Locally with Python

#### Step 1: Open Terminal in the project directory
```bash
cd c:\Users\sekhar\OneDrive\Desktop\SLA-Monitoring-Engine
```

#### Step 2: Install Dependencies
```bash
python -m pip install -r requirements.txt
```

#### Step 3: Start the Monitoring Engine
```bash
python run.py
```

#### Step 4: Open in Your Browser
Visit: **[http://localhost:5000](http://localhost:5000)**

You will see the dashboard running live with pre-seeded services, streaming real-time metrics every 2 seconds!

---

### Option 2: Run with Docker & Docker Compose

#### With Docker Compose (Recommended for containers):
```bash
docker-compose up --build
```

#### Or with standard Docker:
```bash
docker build -t sla-monitoring-engine .
docker run -p 5000:5000 sla-monitoring-engine
```

Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🧪 Running Automated Tests

Run the complete test suite (26 unit and integration tests):

```bash
python -m pytest
```

Output:
```text
============================= test session starts =============================
collected 26 items

tests/test_api.py::test_api_health PASSED                                [  3%]
tests/test_api.py::test_dashboard_renders PASSED                         [  7%]
tests/test_api.py::test_api_overview PASSED                              [ 11%]
tests/test_api.py::test_api_services PASSED                              [ 15%]
tests/test_api.py::test_api_create_and_delete_service PASSED             [ 19%]
tests/test_api.py::test_api_metrics_history PASSED                       [ 23%]
tests/test_api.py::test_api_slos_and_update PASSED                       [ 26%]
tests/test_api.py::test_api_simulator_inject_and_reset PASSED            [ 30%]
tests/test_api.py::test_api_export_report_csv PASSED                     [ 34%]
tests/test_evaluator.py::test_calculate_availability PASSED              [ 38%]
tests/test_evaluator.py::test_calculate_success_rate PASSED              [ 42%]
tests/test_evaluator.py::test_calculate_error_rate PASSED                [ 46%]
tests/test_evaluator.py::test_calculate_error_budget_greater_equal PASSED [ 50%]
tests/test_evaluator.py::test_calculate_error_budget_less_equal PASSED   [ 53%]
tests/test_evaluator.py::test_evaluate_slo_status_greater_equal PASSED   [ 57%]
tests/test_evaluator.py::test_evaluate_slo_status_less_equal PASSED      [ 61%]
tests/test_evaluator.py::test_determine_overall_status PASSED            [ 65%]
tests/test_evaluator.py::test_evaluate_service_slos PASSED               [ 69%]
tests/test_models.py::test_init_db_and_defaults PASSED                   [ 73%]
tests/test_models.py::test_service_crud PASSED                           [ 76%]
tests/test_models.py::test_metrics_insert_and_history PASSED             [ 80%]
tests/test_models.py::test_alerts_lifecycle PASSED                       [ 84%]
tests/test_models.py::test_simulation_configs PASSED                     [ 88%]
tests/test_simulator.py::test_simulator_single_tick PASSED               [ 92%]
tests/test_simulator.py::test_chaos_latency_spike PASSED                 [ 96%]
tests/test_simulator.py::test_chaos_total_outage_triggers_critical_alert PASSED [100%]

============================= 26 passed in 9.57s ==============================
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web UI Dashboard |
| `GET` | `/api/health` | Healthcheck and simulator state |
| `GET` | `/api/overview` | Aggregated fleet metrics, status counts, and active alerts |
| `GET` | `/api/services` | List all monitored services with latest metrics & evaluated status |
| `GET` | `/api/services/<id>` | Detailed service metadata and current SLO evaluations |
| `POST` | `/api/services` | Register a new microservice |
| `PUT` | `/api/services/<id>` | Update service details |
| `DELETE` | `/api/services/<id>` | Remove service and cascade metrics |
| `GET` | `/api/services/<id>/metrics` | Retrieve time-series metric samples (`?limit=60`) |
| `GET` | `/api/services/<id>/slos` | Get service SLO targets |
| `PUT` | `/api/services/<id>/slos/<slo_id>` | Edit SLO/SLA target thresholds |
| `GET` | `/api/alerts` | Get alerts stream (`?status=ACTIVE|RESOLVED|ALL`) |
| `POST` | `/api/alerts/<id>/ack` | Acknowledge an alert |
| `POST` | `/api/alerts/<id>/resolve` | Resolve an alert |
| `POST` | `/api/alerts/clear-resolved` | Delete resolved alerts |
| `POST` | `/api/simulator/inject` | Inject chaos scenario (`ERROR_FLOOD`, `LATENCY_SPIKE`, etc.) |
| `POST` | `/api/simulator/reset` | Reset all services to healthy baseline |
| `POST` | `/api/simulator/toggle` | Pause / resume simulator background engine |
| `POST` | `/api/simulator/tick` | Force a single simulation tick step |
| `GET` | `/api/export/report` | Download CSV compliance audit report |

---

## 🎮 Hands-On Chaos Experiments

Try these experiments in the dashboard to watch SRE in action:

1. **Trigger an SLA Breach**:
   - In the Chaos Control Panel, select **"🚨 Total Service Outage"** and click **Inject Failure Condition**.
   - Watch the service turn **CRITICAL (Red)**.
   - Notice the **Fleet Error Budget** drop to 0% and an instant **Critical Alert** raised in the live feed.
2. **Observe Error Budget Burning**:
   - Select **"💥 500 Error Flood"**.
   - Watch the Error Budget Burn Rate jump above `15.0x` and the Error Budget progress bar drain rapidly.
3. **Simulate a Slow Database**:
   - Select **"🐌 Database Lag"**.
   - Watch P95 Latency spike above 800ms and trigger a **WARNING** status while Availability remains 100%.
4. **Self-Healing Recovery**:
   - Click **"🔄 Reset All to Healthy"**.
   - The metrics return to normal, and open alerts are **automatically marked as Resolved**!

---

## 📄 License
MIT License. Built for learning and production SRE monitoring demonstrations.

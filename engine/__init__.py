import os
from flask import Flask
from flask_cors import CORS
from engine.config import Config, TestConfig
from engine.database import init_db
from engine.simulator import TrafficSimulator
from engine.routes import api_bp

def create_app(test_config=None, start_simulator=True):
    """Application factory for the SLA/SLO Monitoring Engine."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    )

    if test_config:
        app.config.from_object(test_config)
    else:
        app.config.from_object(Config)

    CORS(app)

    # Initialize database tables and default services/SLOs
    db_path = app.config["DATABASE"]
    init_db(db_path, seed_defaults=True)

    # Setup traffic simulator
    simulator = TrafficSimulator(
        db_path=db_path,
        interval_sec=app.config.get("SIMULATOR_INTERVAL_SEC", 2.0)
    )
    app.simulator = simulator

    # If running live (and not in test mode), seed some initial historical points
    if not app.config.get("TESTING"):
        # Generate 15 baseline ticks so charts are populated immediately
        for _ in range(15):
            simulator.step_tick()

        if app.config.get("SIMULATOR_ENABLED", True) and start_simulator:
            simulator.start()

    # Register routes
    app.register_blueprint(api_bp)

    return app

import argparse
import sys
import os

# Ensure safe UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from engine import create_app

def main():
    parser = argparse.ArgumentParser(description="Run the SLA/SLO/SLI Monitoring Engine")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument("--no-sim", action="store_true", help="Disable the background traffic simulator")

    args = parser.parse_args()

    # Disable simulator if --no-sim passed
    start_sim = not args.no_sim

    app = create_app(start_simulator=start_sim)

    print("=" * 70)
    print("  * SLA / SLO / SLI MONITORING ENGINE")
    print("  Site Reliability Engineering Observability & Chaos Control Platform")
    print("=" * 70)
    print(f"  * Dashboard URL:       http://{args.host}:{args.port}")
    print(f"  * Healthcheck API:     http://{args.host}:{args.port}/api/health")
    print(f"  * Overview API:        http://{args.host}:{args.port}/api/overview")
    print(f"  * Traffic Simulator:   {'Active (Ticking every 2s)' if start_sim else 'Disabled'}")
    print("=" * 70)
    print("  Press Ctrl+C to stop the engine.\n")

    try:
        app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[Engine] Shutting down gracefully...")
        if hasattr(app, "simulator") and app.simulator:
            app.simulator.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()

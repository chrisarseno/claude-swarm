#!/usr/bin/env python3
"""Start the Claude Swarm API server."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from swarm.api.server import start_server
from swarm.utils.config import load_config


def main():
    """Main entry point."""
    config_path = Path("config/swarm.yaml")
    config = load_config(config_path if config_path.exists() else None)

    print(f"""
    === Claude Swarm API Server ===

    Starting server on {config.api.host}:{config.api.port}

    API Documentation: http://localhost:{config.api.port}/docs
    WebSocket Stream:  ws://localhost:{config.api.port}/ws/stream

    Press Ctrl+C to stop
    """)

    start_server(
        host=config.api.host,
        port=config.api.port,
        reload=False
    )


if __name__ == "__main__":
    main()

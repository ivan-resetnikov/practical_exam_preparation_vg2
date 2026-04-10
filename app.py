"""
Praksisk eksamen forberedelse Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.
"""

import logging
import vendor.moeserver.server as server


logging.basicConfig()


if __name__ == "__main__":
    app = server.App()

    @app.route("/")
    def route_index() -> bytes:
        return "<h1>/ - Index</h1>".encode("utf-8")

    app.serve_until_KeyboardInterrupt("localhost", 8001)

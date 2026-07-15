from flask import current_app, g, request

from app.extensions import sock
from app.services.runtime_exec_socket import RuntimeExecSocketBridge


@sock.route("/api/runtime/exec/<ticket>")
def runtime_exec(websocket, ticket):
    RuntimeExecSocketBridge(
        current_app.extensions["runtime_exec_registry"],
        idle_timeout=current_app.config.get(
            "RUNTIME_EXEC_IDLE_TIMEOUT_SECONDS", 900
        ),
    ).run(
        websocket,
        ticket,
        g.current_user,
        request.headers.get("Origin"),
        current_app.config["CORS_ORIGINS"],
    )

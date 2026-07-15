import json
import time

from app.extensions import db
from app.utils.errors import ApiError

from .kubernetes_cluster_service import KubernetesClusterService


class RuntimeExecSocketBridge:
    def __init__(self, registry, idle_timeout=900, clock=time.monotonic):
        self.registry = registry
        self.idle_timeout = idle_timeout
        self.clock = clock

    def run(self, websocket, ticket, actor, origin, allowed_origins):
        if origin not in allowed_origins:
            raise ApiError("终端连接来源不受信任", 403, "EXEC_ORIGIN_REJECTED")
        session = self.registry.consume(ticket, actor.id)
        payload = session.payload
        context = payload["context"]
        audit = payload["audit"]
        stream = None
        last_activity = self.clock()
        try:
            stream = KubernetesClusterService().client(
                context.cluster
            ).open_application_pod_exec(
                payload["pod"],
                context.namespace,
                context.application.name,
                payload["container"],
            )
            while stream.is_open():
                stream.update(timeout=0.1)
                if stream.peek_stdout():
                    websocket.send(json.dumps({
                        "type": "stdout", "data": stream.read_stdout()
                    }))
                    last_activity = self.clock()
                if stream.peek_stderr():
                    websocket.send(json.dumps({
                        "type": "stderr", "data": stream.read_stderr()
                    }))
                    last_activity = self.clock()
                try:
                    raw = websocket.receive(timeout=0.1)
                except TimeoutError:
                    raw = ""
                if raw is None:
                    break
                if raw:
                    frame = json.loads(raw)
                    frame_type = frame.get("type")
                    if frame_type == "stdin":
                        stream.write_stdin(str(frame.get("data") or ""))
                    elif frame_type == "resize":
                        stream.write_channel(4, json.dumps({
                            "Width": int(frame.get("cols") or 80),
                            "Height": int(frame.get("rows") or 24),
                        }))
                    elif frame_type == "close":
                        break
                    last_activity = self.clock()
                if self.clock() - last_activity >= self.idle_timeout:
                    websocket.send(json.dumps({
                        "type": "status", "status": "idle-timeout"
                    }))
                    break
            audit.finish("Succeeded")
            db.session.commit()
        except Exception as exc:
            message = exc.message if isinstance(exc, ApiError) else "终端会话异常结束"
            audit.finish("Failed", message)
            db.session.commit()
            raise
        finally:
            if stream is not None:
                stream.close()
            self.registry.release(ticket)

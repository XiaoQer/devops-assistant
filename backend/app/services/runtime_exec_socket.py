import json
import time

from app.extensions import db
from app.models import Application, Project, RuntimeOperationAudit
from app.utils.errors import ApiError

from .delivery_context_service import DeliveryContextService
from .kubernetes_cluster_service import KubernetesClusterService


class RuntimeExecSocketBridge:
    def __init__(self, registry, idle_timeout=900, clock=time.monotonic):
        self.registry = registry
        self.idle_timeout = idle_timeout
        self.clock = clock

    def run(self, websocket, ticket, actor, origin, allowed_origins):
        if origin not in allowed_origins:
            # The ticket was issued before the WebSocket handshake. Release it
            # on handshake rejection so a failed first attempt cannot reserve
            # the target until the TTL expires.
            self.registry.release(ticket)
            raise ApiError("终端连接来源不受信任", 403, "EXEC_ORIGIN_REJECTED")
        session = self.registry.consume(ticket, actor.id)
        payload = session.payload
        stream = None
        audit = None
        last_activity = self.clock()
        try:
            context, audit = self._rehydrate(payload)
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
                    # simple-websocket returns None both for a receive timeout
                    # and for a closed socket. Only the latter ends the exec
                    # session; an idle client must remain connected.
                    if getattr(websocket, "connected", True) is False:
                        break
                    raw = ""
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
            if audit is not None:
                audit.finish("Failed", message)
                db.session.commit()
            raise
        finally:
            if stream is not None:
                stream.close()
            self.registry.release(ticket)

    @staticmethod
    def _rehydrate(payload):
        context_ref = payload.get("context_ref")
        if context_ref:
            project = Project.query.get(context_ref["project_id"])
            application = Application.query.filter_by(
                id=context_ref["application_id"],
                project_id=project.id if project else None,
            ).first() if project else None
            if not project or not application:
                raise ApiError("终端上下文已失效", 404, "EXEC_CONTEXT_NOT_FOUND")
            context = DeliveryContextService().resolve(
                project, application, context_ref["environment"]
            )
            audit = RuntimeOperationAudit.query.get(payload["audit_id"])
            if not audit:
                raise ApiError("终端审计记录不存在", 404, "EXEC_AUDIT_NOT_FOUND")
            return context, audit
        # Backward-compatible fallback for tickets issued before context IDs
        # were introduced; new tickets never carry ORM instances.
        return payload["context"], payload["audit"]

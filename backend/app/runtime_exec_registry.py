import secrets
import threading
import time
from dataclasses import dataclass

from app.utils.errors import ApiError


@dataclass
class RuntimeExecTicket:
    ticket: str
    actor_id: int
    target: tuple
    payload: dict
    issued_at: float
    expires_at: float
    consumed: bool = False


class RuntimeExecRegistry:
    def __init__(
        self,
        ticket_ttl=60,
        max_per_user=2,
        max_per_target=1,
        clock=time.monotonic,
    ):
        self.ticket_ttl = ticket_ttl
        self.max_per_user = max_per_user
        self.max_per_target = max_per_target
        self.clock = clock
        self._tickets = {}
        self._lock = threading.Lock()

    def issue(self, actor_id, target, payload):
        with self._lock:
            self._remove_expired()
            active = list(self._tickets.values())
            if sum(item.actor_id == actor_id for item in active) >= self.max_per_user:
                raise ApiError(
                    "当前用户的终端会话数已达上限", 429, "EXEC_USER_LIMIT"
                )
            if sum(item.target == target for item in active) >= self.max_per_target:
                raise ApiError("目标容器已有终端会话", 409, "EXEC_TARGET_BUSY")
            value = secrets.token_urlsafe(32)
            now = self.clock()
            self._tickets[value] = RuntimeExecTicket(
                ticket=value,
                actor_id=actor_id,
                target=target,
                payload=payload,
                issued_at=now,
                expires_at=now + self.ticket_ttl,
            )
            return value

    def consume(self, ticket, actor_id):
        with self._lock:
            item = self._tickets.get(ticket)
            if item and self.clock() > item.expires_at:
                self._tickets.pop(ticket, None)
                raise ApiError("终端票据已过期", 410, "EXEC_TICKET_EXPIRED")
            if not item or item.consumed or item.actor_id != actor_id:
                raise ApiError("终端票据无效", 403, "EXEC_TICKET_INVALID")
            item.consumed = True
            return item

    def release(self, ticket):
        with self._lock:
            return self._tickets.pop(ticket, None)

    def _remove_expired(self):
        now = self.clock()
        for ticket, item in list(self._tickets.items()):
            if now > item.expires_at and not item.consumed:
                self._tickets.pop(ticket, None)

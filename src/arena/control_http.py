"""Authenticated HTTP routes for the private control service."""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

from .control_types import ControlError, _decode


def dispatch_http(handler, service):
    """Return True only for dedicated authenticated control endpoints."""
    parsed = urlsplit(handler.path)
    parts = parsed.path.strip("/").split("/")
    if parts[:2] not in (["api", "queue"], ["api", "control"]):
        return False
    try:
        principal = service.authenticate(handler.headers.get("Authorization"))
        method = handler.command
        if method == "GET" and parts == ["api", "control", "templates"]:
            value = service.templates(principal)
        elif method == "GET" and parts == ["api", "control", "results"]:
            from .results import results
            value = results(service, principal)
        elif method == "GET" and parts == ["api", "queue"]:
            query = parse_qs(parsed.query)
            value = service.queue(principal, limit=int(query.get("limit", ["200"])[0]), offset=int(query.get("offset", ["0"])[0]))
        elif method == "GET" and len(parts) == 3 and parts[:2] == ["api", "queue"]:
            value = service.detail(principal, parts[2])
        elif method == "GET" and len(parts) == 4 and parts[:2] == ["api", "queue"] and parts[3] == "logs":
            query = parse_qs(parsed.query)
            value = service.logs(principal, parts[2], stream=query.get("stream", ["stdout"])[0], cursor=int(query.get("cursor", ["0"])[0]), limit=int(query.get("limit", ["16384"])[0]), tail=query.get("tail", ["false"])[0] == "true")
        elif method == "POST":
            if handler.headers.get("Transfer-Encoding"):
                raise ControlError("Chunked control requests are not supported")
            length = int(handler.headers.get("Content-Length", "0"))
            if not 0 <= length <= 32768:
                raise ControlError("Request body exceeds limit", 413)
            handler.connection.settimeout(10)
            body = _decode(handler.rfile.read(length)) if length else {}
            if parts == ["api", "queue"]:
                value = service.submit(principal, body)
            elif len(parts) == 4 and parts[:2] == ["api", "queue"] and parts[3] == "cancel":
                if body:
                    raise ControlError("Cancel takes an empty object")
                value = service.cancel(principal, parts[2])
            elif parts == ["api", "control", "reload"]:
                service._scope(principal, "admin")
                if body:
                    raise ControlError("Reload takes an empty object")
                value = {"schema": "arena.control-reload/1", "revision": service.reload()}
            else:
                raise ControlError("Control route not found", 404)
        else:
            raise ControlError("Control route not found", 404)
        handler.reply(value)
    except ControlError as exc:
        handler.close_connection = True
        handler.reply({"error": str(exc)}, exc.status)
    except (ValueError, TypeError):
        handler.close_connection = True
        handler.reply({"error": "Invalid control request"}, 400)
    except Exception:
        handler.close_connection = True
        handler.reply({"error": "Control service is unavailable"}, 503)
    return True

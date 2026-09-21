"""Local HTTP and server-sent events; never imports or executes experiment code."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .observers.sciel.data import RunStore
from .registry import RegistryError, get_catalog, get_participants

STATIC = Path(__file__).resolve().parents[2] / "web"
if not STATIC.is_dir():
    STATIC = Path(__file__).with_name("_assets") / "web"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def observer_cache_dir(roots, requested):
    """Persist observational timing only outside every watched directory."""
    if requested is None:
        return None
    cache = Path(requested).expanduser().resolve()
    for root in roots:
        watched = Path(root).expanduser().resolve()
        if cache.is_relative_to(watched) or watched.is_relative_to(cache):
            return None
    return cache


def default_timing_cache_dir(roots):
    configured = os.environ.get("XDG_CACHE_HOME")
    base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".cache"
    return observer_cache_dir(roots, base / "arena" / "timing")


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, roots, *, timing_cache_dir=None, registry_root=None, control=None):
        if control is not None:
            import ipaddress
            if not ipaddress.ip_address(address[0]).is_loopback:
                raise ValueError("Private control must bind to a loopback address")
        self.control = control
        self.registry_root = registry_root
        roots = [Path(root) for root in roots]
        self.store = RunStore(roots, timing_cache_dir=observer_cache_dir(roots, timing_cache_dir))
        self.store_lock = threading.RLock()
        self.stopping = threading.Event()
        super().__init__(address, Handler)
        self.timing_thread = threading.Thread(target=self._observe_timings,
                                             name='arena-observer-timing', daemon=True)
        self.timing_thread.start()

    def _observe_timings(self):
        while not self.stopping.is_set():
            try:
                self.store.poll_timings()
            except Exception as exc:
                logging.getLogger('arena.observers.sciel').warning('Timing monitor unavailable (%s)', type(exc).__name__)
            if self.stopping.wait(2):
                break

    def shutdown(self):
        self.stopping.set()
        super().shutdown()

    def server_close(self):
        self.stopping.set()
        thread = getattr(self, 'timing_thread', None)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if args and str(args[1] if len(args) > 1 else "").startswith("5"):
            super().log_message(fmt, *args)

    def send_headers(self, code, content_type, length=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def reply(self, value, code=200):
        body = encoded(value)
        self.send_headers(code, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def do_GET(self):
        try:
            self.route()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except RegistryError:
            self.reply({"error": "Registry unavailable or invalid."}, 503)
        except (KeyError, FileNotFoundError, ValueError):
            self.reply({"error": "Run or program not found."}, 404)
        except Exception:
            # Do not expose filesystem paths, config values or tracebacks over HTTP.
            self.reply({"error": "Unable to read data. Please try again."}, 500)

    def do_POST(self):
        if self.server.control is not None:
            from .control import dispatch_http
            if dispatch_http(self, self.server.control):
                return
        self.close_connection = True
        self.reply({"error": "Page not found."}, 404)

    def route(self):
        if self.server.control is not None:
            from .control import dispatch_http
            if dispatch_http(self, self.server.control):
                return
        parsed = urlsplit(self.path)
        parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
        if parts == ["api", "health"]:
            from . import __version__
            self.reply({"status": "ok", "component": "arena", "version": __version__,
                        "mode": "read_only" if self.server.control is None else "private_control", "observer": "sciel",
                        "capabilities": {"catalog": True, "participants": True, "insights": True,
                                         "references": True, "search_families": True,
                                         "run_observation": True, "launch": self.server.control is not None}})
            return
        if parts == ["api", "catalog"]:
            self.reply(get_catalog(self.server.registry_root))
            return
        if parts == ["api", "participants"]:
            self.reply(get_participants(self.server.registry_root))
            return
        if parts == ["api", "insights"]:
            from .insights import get_insights
            self.reply(get_insights(self.server.registry_root))
            return
        if parts == ["api", "references"]:
            from .references import get_references
            self.reply(get_references(self.server.registry_root))
            return
        if parts == ["api", "search-families"]:
            from .search_families import get_search_families
            self.reply(get_search_families(self.server.registry_root))
            return
        if parts == ["api", "results-overview"]:
            from .results_overview import get_results_overview
            self.reply(get_results_overview(self.server.registry_root))
            return
        if parts == ["api", "runs"]:
            with self.server.store_lock:
                payload = {"runs": self.server.store.discover(), "refresh_seconds": 2}
            self.reply(payload)
            return
        if len(parts) == 3 and parts[:2] == ["api", "runs"]:
            with self.server.store_lock:
                payload = self.server.store.snapshot(parts[2])
            self.reply(payload)
            return
        if len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] == "program":
            with self.server.store_lock:
                payload = self.server.store.detail(parts[2], parts[4])
            self.reply(payload)
            return
        if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == 'packings':
            query = parse_qs(parsed.query)
            try:
                with self.server.store_lock:
                    payload = self.server.store.packings(parts[2],
                        offset=int(query.get('offset', ['0'])[0]),
                        limit=int(query.get('limit', ['120'])[0]),
                        sort=query.get('sort', ['score'])[0],
                        island=query.get('island', ['all'])[0], query=query.get('q', [''])[0])
            except ValueError:
                self.reply({'error': 'Invalid packing page or filter.'}, 400)
                return
            self.reply(payload)
            return
        if len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] in {"method", "proposal"}:
            with self.server.store_lock:
                view = self.server.store._methods(self.server.store._path(parts[2]))
                payload = view.method_detail(parts[4]) if parts[3] == 'method' else view.proposal_detail(parts[4])
            self.reply(payload)
            return
        if len(parts) == 5 and parts[:2] == ["api", "runs"] and parts[3] in {"research-tools", "research-tool-artifacts", "research-cells", "research-tool-jobs"}:
            with self.server.store_lock:
                read = {'research-tools':self.server.store.research_tool,'research-tool-artifacts':self.server.store.research_tool_artifact,'research-cells':self.server.store.research_cell,'research-tool-jobs':self.server.store.research_tool_job}[parts[3]]
                payload = read(parts[2], parts[4])
            self.reply(payload)
            return
        if len(parts) in (4, 5) and parts[:2] == ["api", "runs"] and parts[3] == "workflow":
            with self.server.store_lock:
                if len(parts) == 5:
                    payload = self.server.store.workflow_detail(parts[2], parts[4])
                else:
                    query = parse_qs(parsed.query)
                    payload = self.server.store.workflow(parts[2],
                        limit=int(query.get('limit', ['60'])[0]),
                        before=query.get('before', [None])[0],
                        actor=query.get('actor', ['all'])[0], query=query.get('q', [''])[0])
            self.reply(payload)
            return
        if len(parts) in (4, 5) and parts[:2] == ["api", "runs"] and parts[3] == "llm-calls":
            with self.server.store_lock:
                if len(parts) == 5:
                    payload = self.server.store.llm_call(parts[2], parts[4])
                else:
                    query = parse_qs(parsed.query)
                    payload = self.server.store.llm_calls(parts[2],
                        offset=int(query.get('offset', ['0'])[0]),
                        limit=int(query.get('limit', ['50'])[0]),
                        query=query.get('q', [''])[0])
            self.reply(payload)
            return
        if parts == ["api", "stream"]:
            run_id = parse_qs(parsed.query).get("run", [""])[0]
            self.stream(run_id)
            return
        if not parts or parts == ["index.html"]:
            file = STATIC / "index.html"
        elif parts in (["experiments"], ["experiment.html"]):
            file = STATIC / "experiment.html"
        elif parts in (["experiments", "queue"], ["queue"], ["queue.html"]):
            file = STATIC / "queue.html"
        elif parts in (["experiments", "results"], ["experiment-results.html"]):
            file = STATIC / "experiment-results.html"
        elif parts in (["results"], ["results.html"]):
            file = STATIC / "results.html"
        elif len(parts) == 1 and parts[0] in {"arena.js", "arena.css", "arena-insights.js", "arena-insights.css",
                                             "arena-atlas.js", "arena-atlas.css", "arena-theme.css",
                                             "arena-contribute.js", "arena-contribute.css", "arena-queue.js", "arena-queue.css",
                                             "arena-results.js", "arena-results.css", "arena-workspace.css",
                                             "arena-results-showcase.js", "arena-results-showcase.css",
                                             "arena-results-overview.js", "arena-results-overview.css",
                                             "results-research.js", "results-efficiency.js", "results-rsi.js"}:
            file = STATIC / parts[0]
        elif len(parts) == 2 and parts[0] == "brand" and parts[1] in {"cpil.png", "mbzuai.png"}:
            file = STATIC / "brand" / parts[1]
        elif len(parts) == 1 and parts[0] in {"app.js", "style.css", "effort.js", "effort.css", "chart.js", "learning.js", "llm_calls.js", "llm_calls.css", "architecture.js", "architecture.css", "population.js", "population.css", "storage-view.js", "population-preview.js", "population-preview.css", "methods.js", "methods.css", "methods_progress.js", "methods_progress.css", "methods_atlas.js", "methods_atlas.css", "research_tools.js", "research_tools.css", "research_cells.js", "research_cells.css", "workflow.js", "workflow.css", "packings.js", "packings.css", "favicon.svg"}:
            file = STATIC / parts[0]
        else:
            self.reply({"error": "Page not found."}, 404)
            return
        body = file.read_bytes()
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if mime.startswith("text/") or file.suffix == ".js":
            mime += "; charset=utf-8"
        self.send_headers(200, mime, len(body))
        self.wfile.write(body)

    def stream(self, run_id):
        with self.server.store_lock:
            version, event, payload = self.server.store.stream_update(run_id)
        body = encoded(payload)
        self.connection.settimeout(15)
        # SSE is an indefinite body. Close on termination so HTTP/1.1 clients
        # do not wait for another frame after shutdown or run disappearance.
        self.close_connection = True
        self.send_headers(200, "text/event-stream; charset=utf-8")
        previous_runtime = None
        last_heartbeat = 0
        while not self.server.stopping.is_set():
            if event == "snapshot" or body != previous_runtime:
                self.wfile.write(b"event: " + event.encode("ascii") + b"\ndata: " + body + b"\n\n")
                self.wfile.flush()
                if event == "runtime":
                    previous_runtime = body
                last_heartbeat = time.monotonic()
            elif time.monotonic() - last_heartbeat > 10:
                self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
                last_heartbeat = time.monotonic()
            if self.server.stopping.wait(2):
                break
            try:
                with self.server.store_lock:
                    version, event, payload = self.server.store.stream_update(run_id, version)
                body = encoded(payload)
            except (KeyError, FileNotFoundError, ValueError):
                self.wfile.write(b'event: unavailable\ndata: {}\n\n')
                self.wfile.flush()
                break


def serve(roots, port=8787):
    server = DashboardServer(("127.0.0.1", port), roots,
                             timing_cache_dir=default_timing_cache_dir(roots))
    print(f"Arena: http://127.0.0.1:{server.server_port}", flush=True)
    print("Watching: " + ", ".join(str(Path(root).resolve()) for root in roots), flush=True)
    print("Read-only monitor. Ctrl+C stops the dashboard, not the experiment.", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stopping.set()
        server.server_close()

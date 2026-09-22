"""Local HTTP/SSE checks using only stdlib and inert temporary artifacts."""

from __future__ import annotations

from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from arena.server import DashboardServer, Handler


class DashboardServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runs_root = self.root / "runs"
        self.run = self.runs_root / "example"
        self.run.mkdir(parents=True)
        self.journal = self.run / "sciel_events.jsonl"
        self.executed = self.root / "candidate_was_executed"
        self.parent_code = "value = 1\n"
        self.child_code = (
            "from pathlib import Path\n"
            f"Path({str(self.executed)!r}).write_text('unexpected execution')\n"
            "value = 2\n"
        )
        self.sequence = 0
        self.append(event="run_start", task="fixture/task", seed=4,
                    counters=dict(cost_total=0, seed_score=1, B_evals=0, iteration_no=0))
        self.append(event="iteration", iteration_no=1, B_evals=1, island=0,
                    parent_id="p1", child_id="p2", child_code=self.child_code,
                    child_score=2, pop_best=2, cost=.1)
        checkpoint = dict(
            iteration_no=1, B_evals=1, cost_total=.1, seed_score=1,
            db=dict(pop_best_id="p2", programs=[
                dict(id="p1", parent_id=None, code=self.parent_code, score=1),
                dict(id="p2", parent_id="p1", code=self.child_code, score=2),
            ]),
            provenance=dict(run_id="fixture-run", journal_anchor=dict(
                segment_id="fixture-segment", event_seq=self.sequence)),
        )
        (self.run / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
        self.private_file = self.root / "private.txt"
        self.private_file.write_text("outside-root-private-content", encoding="utf-8")
        self.server = DashboardServer(("127.0.0.1", 0), [self.runs_root])
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs=dict(poll_interval=.05), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def append(self, **row):
        self.sequence += 1
        record = dict(run_id="fixture-run", segment_id="fixture-segment",
                      event_seq=self.sequence, **row)
        with self.journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")

    def connection(self):
        return http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=8)

    def get(self, path):
        with closing(self.connection()) as connection:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def run_id(self):
        status, _, body = self.get("/api/runs")
        self.assertEqual(status, 200)
        runs = json.loads(body)["runs"]
        self.assertEqual(len(runs), 1)
        return runs[0]["id"]

    def fingerprints(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    @staticmethod
    def sse_snapshot(response):
        """Read a complete snapshot event, ignoring comment heartbeats."""
        event, data = None, []
        for _ in range(100):
            line = response.readline()
            if not line:
                raise AssertionError("SSE ended before a snapshot")
            if line in (b"\n", b"\r\n"):
                if event == "snapshot":
                    return json.loads(b"\n".join(data))
                event, data = None, []
            elif line.startswith(b"event: "):
                event = line[7:].strip().decode()
            elif line.startswith(b"data: "):
                data.append(line[6:].rstrip(b"\r\n"))
        raise AssertionError("No complete SSE snapshot frame")

    def test_static_assets_and_api_preserve_sources_without_execution(self):
        before = self.fingerprints()
        for path, mime in [("/", "text/html"), ("/index.html", "text/html"),
                           ("/experiments", "text/html"), ("/experiment.html", "text/html"),
                           ("/results", "text/html"), ("/results.html", "text/html"),
                           ("/experiments/results", "text/html"), ("/experiment-results.html", "text/html"),
                           ("/experiments/queue", "text/html"), ("/queue", "text/html"),
                           ("/arena-workspace.css", "text/css"),
                           ("/arena-results-showcase.js", "javascript"), ("/arena-results-showcase.css", "text/css"),
                           ("/arena-results-overview.js", "javascript"), ("/arena-results-overview.css", "text/css"),
                           ("/research-map.js", "javascript"), ("/research-map.css", "text/css"),
                           ("/research-map-layout.js", "javascript"), ("/research-map-model.js", "javascript"),
                           ("/research-map-inspector.js", "javascript"),
                           ("/results-research.js", "javascript"), ("/results-efficiency.js", "javascript"), ("/results-rsi.js", "javascript"),
                           ("/arena.js", "javascript"), ("/arena.css", "text/css"),
                           ("/arena-insights.js", "javascript"), ("/arena-insights.css", "text/css"),
                           ("/arena-atlas.js", "javascript"), ("/arena-atlas.css", "text/css"),
                           ("/arena-theme.css", "text/css"),
                           ("/app.js", "javascript"), ("/chart.js", "javascript"),
                           ("/learning.js", "javascript"),
                           ("/population.js", "javascript"), ("/population.css", "text/css"),
                           ("/storage-view.js", "javascript"),
                           ("/population-preview.js", "javascript"),
                           ("/population-preview.css", "text/css"),
                           ("/research_tools.js", "javascript"), ("/research_tools.css", "text/css"),
                           ("/research_cells.js", "javascript"), ("/research_cells.css", "text/css"),
                           ("/methods_progress.js", "javascript"), ("/methods_progress.css", "text/css"),
                           ("/methods_atlas.js", "javascript"), ("/methods_atlas.css", "text/css"),
                           ("/style.css", "text/css"), ("/favicon.svg", "image/svg+xml")]:
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertIn(mime, headers["Content-Type"])
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(int(headers["Content-Length"]), len(body))
                self.assertTrue(body)
        ident = self.run_id()
        status, _, body = self.get(f"/api/runs/{ident}")
        self.assertEqual(status, 200)
        snapshot = json.loads(body)
        self.assertEqual(snapshot["stats"]["best_score"], 2)
        self.assertEqual(snapshot["stats"]["evaluations"], 1)
        self.assertEqual(snapshot["trials"][0]["parent_id"], "p1")
        status, _, body = self.get(f"/api/runs/{ident}/program/p2")
        self.assertEqual(status, 200)
        detail = json.loads(body)
        self.assertEqual(detail["code"], self.child_code)
        self.assertEqual(detail["parent_code"], self.parent_code)
        self.assertEqual(detail["diff_kind"], "full_sources")
        self.assertIn("-value = 1", detail["diff"])
        self.assertIn("+value = 2", detail["diff"])
        self.assertFalse(self.executed.exists())
        self.assertEqual(self.fingerprints(), before)

    def test_results_overview_reads_only_explicit_snapshot_without_control_key(self):
        from arena.results_overview import build_results_overview
        class PrivateControlMustNotBeRead:
            def authenticate(self, authorization):
                raise AssertionError("Published results must not consult private control credentials")
        self.server.control = PrivateControlMustNotBeRead()
        published = build_results_overview(dict(schema="arena.results/1", generated_at=100,
            total=0, truncated=False, runs=[]), generated_at=101)
        registry = self.root / "registry"
        registry.mkdir()
        snapshot = registry / "results-overview.json"
        snapshot.write_text(json.dumps(published), encoding="utf-8")
        self.server.registry_root = registry
        before = self.fingerprints()
        status, headers, body = self.get("/api/results-overview")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(body), published)
        self.assertEqual(self.fingerprints(), before)
        self.assertFalse(self.executed.exists())
        # Never fall back to private runs when publication is absent or invalid.
        snapshot.write_text(json.dumps({**published, "private": "do-not-publish"}), encoding="utf-8")
        status, _, body = self.get("/api/results-overview")
        self.assertEqual(status, 503)
        self.assertNotIn(b"do-not-publish", body)
        snapshot.unlink()
        self.assertEqual(self.get("/api/results-overview")[0], 503)

    def test_showcase_and_operational_results_keep_separate_navigation(self):
        landing = self.get('/')[2].decode()
        showcase = self.get('/results')[2].decode()
        operational = self.get('/experiments/results')[2].decode()
        queue = self.get('/experiments/queue')[2].decode()
        self.assertNotIn('href="/queue"', landing)
        self.assertNotIn('href="/experiments/queue"', showcase)
        self.assertIn('arena-tabs', showcase)
        self.assertIn('arena-workspace', operational)
        self.assertIn('arena-workspace', queue)
        self.assertIn('href="/experiments/results"', queue)
        self.assertIn('href="/experiments/queue"', operational)
        self.assertEqual(self.get('/queue')[2], self.get('/experiments/queue')[2])
        self.assertNotEqual(showcase, operational)

    def test_arena_registry_routes_are_separate_from_native_run_observation(self):
        before = self.fingerprints()
        status, _, body = self.get('/api/health')
        self.assertEqual(status, 200)
        health = json.loads(body)
        self.assertEqual(health['component'], 'arena')
        self.assertEqual(health['mode'], 'read_only')
        self.assertTrue(health['version'])
        self.assertTrue(health['capabilities']['search_families'])
        self.assertFalse(health['capabilities']['launch'])
        for route, schema, key in (('/api/catalog', 'arena.catalog/1', 'tasks'),
                                   ('/api/insights', 'arena.insights/1', 'task_annotations'),
                                   ('/api/references', 'arena.references/1', 'summary'),
                                   ('/api/search-families', 'arena.search-families/1', 'groups'),
                                   ('/api/participants', 'arena.participants/1', 'participants')):
            status, _, body = self.get(route)
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertEqual(payload['schema'], schema)
            self.assertTrue(payload[key])
        self.assertNotEqual(self.get('/')[2], self.get('/experiments')[2])
        self.assertEqual(self.fingerprints(), before)
        self.assertFalse(self.executed.exists())

    def test_search_family_route_partitions_all_catalog_packages(self):
        before = self.fingerprints()
        status, headers, body = self.get('/api/search-families')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        view = json.loads(body)
        catalog = json.loads(self.get('/api/catalog')[2])
        ids = [ident for group in view['groups'] for ident in group['task_ids']]
        self.assertEqual(len(ids), 959)
        self.assertEqual(len(set(ids)), 959)
        self.assertEqual(set(ids), {task['id'] for task in catalog['tasks']})
        self.assertEqual(view['summary']['corpus_paper_count'], 98)
        self.assertEqual(view['summary']['source_group_count'], 113)
        self.assertEqual(view['task_annotations']['eoh-online-bin-packing']['related_search_family_ids'],
                         ['alphaevolve-openevolve', 'funsearch-eoh', 'other'])
        self.assertEqual(self.fingerprints(), before)
        self.assertFalse(self.executed.exists())

    def test_stale_search_family_data_returns_503_without_exposing_source_paths(self):
        from arena.registry import resolve_registry_root
        source_root = resolve_registry_root()
        custom_registry = self.root / 'registry'
        custom_registry.mkdir()
        for name in ('catalog.json', 'search-family-sources.json', 'search-families.json'):
            (custom_registry / name).write_bytes((source_root / name).read_bytes())
        view = json.loads((custom_registry / 'search-families.json').read_text())
        view['catalog_digest'] = '0' * 64
        (custom_registry / 'search-families.json').write_text(json.dumps(view))
        self.server.registry_root = custom_registry
        status, _, body = self.get('/api/search-families')
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {'error': 'Registry unavailable or invalid.'})
        self.assertNotIn(str(custom_registry).encode(), body)

    def test_unknown_routes_ids_and_path_traversal_cannot_read_files(self):
        before = self.fingerprints()
        ident = self.run_id()
        for path in ["/private.txt", "/../private.txt", "/%2e%2e/private.txt",
                     "/assets/../../private.txt", "/api/runs/unknown",
                     "/api/runs/%2e%2e%2fprivate.txt", "/api/stream?run=unknown",
                     f"/api/runs/{ident}/program/%2e%2e%2fcheckpoint.json"]:
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 404)
                self.assertIn("application/json", headers["Content-Type"])
                self.assertNotIn(b"outside-root-private-content", body)
                self.assertNotIn(str(self.root).encode(), body)
        self.assertEqual(self.fingerprints(), before)

    def test_native_tool_routes_serve_only_journal_bound_verified_artifacts(self):
        def write(folder, body):
            raw = json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
            ident = hashlib.sha256(raw).hexdigest()
            path = self.run / 'research_tools' / folder / (ident + '.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            return ident, path
        tool, source_path = write('objects', dict(schema='sciel-method/1',
            manifest=dict(kind='tool',entrypoint='tool.py:run',parents=[],protocol={'schema':'sciel-research-tool/1'}),
            files={'tool.py':self.child_code}))
        receipt, _ = write('artifacts', dict(schema='sciel-research-tool-artifact/1',kind='proposal',
            payload=dict(action_id='ep',attempt=0,prompt='exact prompt',response={'text':'exact reply'})))
        self.append(event='research_tool',schema='sciel-research-tool-event/1',phase='registered',tool_id=tool)
        self.append(event='research_tool',schema='sciel-research-tool-event/1',phase='llm_result',
            action_id='ep',attempt=0,island_id=0,receipt_id=receipt)
        run = self.run_id()
        before = self.fingerprints()
        status, _, body = self.get(f'/api/runs/{run}/research-tools/{tool}')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['files']['tool.py'],self.child_code)
        status, _, body = self.get(f'/api/runs/{run}/research-tool-artifacts/{receipt}')
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['payload']['response']['text'],'exact reply')
        self.assertEqual(self.fingerprints(),before)
        self.assertFalse(self.executed.exists())
        source_path.write_text('{}')
        self.assertEqual(self.get(f'/api/runs/{run}/research-tools/{tool}')[0],404)
        self.assertEqual(self.get(f'/api/runs/{run}/research-tools/%2e%2e%2fprivate.txt')[0],404)

    def test_llm_inspector_endpoints_serve_saved_text_without_execution(self):
        self.append(event='research', phase='attempt', experiment_id='r1',
                    prompt_sha256=hashlib.sha256(b'unavailable').hexdigest())
        self.append(event='research', phase='hypothesis', experiment_id='r1',
                    response=self.child_code, response_truncated=False)
        before = self.fingerprints()
        ident = self.run_id()
        status, _, body = self.get(f'/api/runs/{ident}/llm-calls?limit=1')
        self.assertEqual(status, 200)
        calls = json.loads(body)
        self.assertEqual(calls['total'], 1)
        self.assertNotIn('response', calls['calls'][0])
        call_id = calls['calls'][0]['id']
        status, _, body = self.get(f'/api/runs/{ident}/llm-calls/{call_id}')
        self.assertEqual(status, 200)
        detail = json.loads(body)
        self.assertEqual(detail['response']['text'], self.child_code)
        self.assertIsNone(detail['prompt']['text'])
        for path in (f'/api/runs/{ident}/llm-calls/%2e%2e%2fprivate.txt',
                     f'/api/runs/{ident}/llm-calls?limit=10000'):
            self.assertEqual(self.get(path)[0], 404)
        for path in ('/llm_calls.js', '/llm_calls.css'):
            self.assertEqual(self.get(path)[0], 200)
        self.assertFalse(self.executed.exists())
        self.assertEqual(self.fingerprints(), before)

    def test_slow_response_does_not_hold_the_shared_store_lock(self):
        """A stalled client must not block other snapshots or the SSE reader."""
        entered, release = threading.Event(), threading.Event()
        original = Handler.reply

        def stalled_reply(handler, value, code=200):
            if handler.path == "/api/runs?slow=1":
                entered.set()
                release.wait(5)
            return original(handler, value, code)

        with patch.object(Handler, "reply", stalled_reply), ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.get, "/api/runs?slow=1")
            try:
                self.assertTrue(entered.wait(3))
                second = pool.submit(self.get, "/api/runs")
                self.assertEqual(second.result(timeout=2)[0], 200)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=3)[0], 200)

    def test_sse_delivers_initial_and_appended_terminal_snapshot(self):
        ident = self.run_id()
        with closing(self.connection()) as connection:
            connection.request("GET", f"/api/stream?run={ident}")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("text/event-stream", response.getheader("Content-Type"))
            initial = self.sse_snapshot(response)
            self.assertEqual(initial["stats"]["best_score"], 2)
            self.assertNotEqual(initial["run"]["status"], "completed")
            self.append(event="iteration", iteration_no=2, B_evals=2, island=0,
                        parent_id="p2", child_id="p3", child_code="value = 3\n",
                        child_score=3, pop_best=3, cost=.2)
            self.append(event="run_end", reason="budget", iteration_no=2, B_evals=2,
                        pop_best=3, cost_total=.3, seed_score=1)
            before = self.fingerprints()
            final = self.sse_snapshot(response)
            self.assertEqual(final["run"]["event_count"], 4)
            self.assertEqual(final["run"]["status"], "completed")
            self.assertEqual(final["run"]["status_reason"], "budget")
            self.assertEqual(final["stats"]["best_score"], 3)
            self.assertEqual(final["stats"]["evaluations"], 2)
            self.assertEqual(final["stats"]["cost_total"], .3)
            self.assertEqual(final["trials"][-1]["parent_id"], "p2")
            self.assertFalse(self.executed.exists())
            self.assertEqual(self.fingerprints(), before)
            response.close()


if __name__ == "__main__":
    unittest.main()

"""Model-driven evaluation families: prompts, agent scaffolds and workflows scored by a language model.

The candidate is a Python program that exposes ``solve(question, llm) -> str``
(or a benchmark-specific variant documented in the task README). ``llm`` is a
budgeted callable ``llm(prompt_or_messages, **options) -> str`` that forwards
to OpenRouter through the same account SCiEL uses (``OPENROUTER_API_KEY`` in
the environment or ``<SCiEL root>/.env``). Every request is cached on disk by
model + messages so repeated evaluations of the same program cost nothing, and
a per-evaluation spending cap (``ARTASK_LLM_BUDGET_USD``, default 0.25) stops
a runaway program.

Benchmarks are drawn from public Hugging Face datasets (``BENCHMARKS``); each
evaluation uses a fixed, seeded sample of ``ARTASK_LLM_SAMPLES`` items
(default 10) so results are comparable across programs and cheap to obtain.
Scores are therefore *estimates on a small sample*, not the papers' full-test
numbers; raise the sample size for a real experiment.
"""
from __future__ import annotations

from arena_task_paths import cache_path, external_path

import hashlib
import json
import math
import os
import re
import sqlite3
import string
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .runtime import CandidateError, require

CACHE_DIR = external_path(os.environ.get("ARTASK_LLM_CACHE", cache_path("llm-cache")))
DEFAULT_MODEL = os.environ.get("ARTASK_LLM_MODEL", "google/gemini-2.5-flash")
SAMPLES = int(os.environ.get("ARTASK_LLM_SAMPLES", "10"))
BUDGET_USD = float(os.environ.get("ARTASK_LLM_BUDGET_USD", "0.25"))
# Conservative list prices (USD per million tokens) for the reservation check.
PRICES = {"google/gemini-2.5-flash": (0.30, 2.50), "google/gemini-2.5-pro": (1.25, 10.0), "openai/gpt-4o-mini": (0.15, 0.60),
          "openai/gpt-4.1-mini": (0.40, 1.60), "anthropic/claude-sonnet-4": (3.0, 15.0), "deepseek/deepseek-chat-v3-0324": (0.27, 1.10)}
UNKNOWN_PRICE = (10.0, 40.0)


def read_api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    for env in (Path(os.environ.get("SCIEL_ROOT", "")) / ".env" if os.environ.get("SCIEL_ROOT") else None,
                Path(__file__).resolve().parents[4] / "SCiEL" / ".env", Path.cwd() / ".env"):
        if env and env.is_file():
            for line in env.read_text().splitlines():
                if line.strip().startswith("OPENROUTER_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise CandidateError("OPENROUTER_API_KEY is not set (environment or SCiEL/.env)")


class Cache:
    def __init__(self, path=CACHE_DIR / "responses.sqlite"):
        path = external_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path), check_same_thread=False)
        self.connection.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, model TEXT, response TEXT, cost REAL, prompt_tokens INTEGER, completion_tokens INTEGER, created REAL)")
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            row = self.connection.execute("SELECT response, cost, prompt_tokens, completion_tokens FROM responses WHERE key=?", (key,)).fetchone()
        return row

    def put(self, key, model, response, cost, prompt_tokens, completion_tokens):
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?,?,?)", (key, model, response, cost, prompt_tokens, completion_tokens, time.time()))
            self.connection.commit()


class LLM:
    """Budgeted, cached chat completion client (OpenRouter, OpenAI-compatible)."""

    def __init__(self, model=DEFAULT_MODEL, budget_usd=BUDGET_USD, max_tokens=1024, temperature=0.0, cache=None, api_key=None):
        self.model, self.budget, self.max_tokens, self.temperature = model, float(budget_usd), int(max_tokens), float(temperature)
        self.cache = cache or Cache()
        self._key = api_key
        self.requests = self.cached = 0
        self.cost = 0.0
        self.prompt_tokens = self.completion_tokens = 0

    @property
    def api_key(self):
        if self._key is None:
            self._key = read_api_key()
        return self._key

    def __call__(self, prompt, *, system=None, max_tokens=None, temperature=None, json_mode=False):
        messages = prompt if isinstance(prompt, list) else ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": str(prompt)}]
        require(all(isinstance(m, dict) and m.get("role") in ("system", "user", "assistant") and isinstance(m.get("content"), str) for m in messages), "messages must be role/content dicts")
        max_tokens = min(int(max_tokens or self.max_tokens), 8192)
        temperature = self.temperature if temperature is None else float(temperature)
        key = hashlib.sha256(json.dumps([self.model, messages, max_tokens, temperature, json_mode], sort_keys=True).encode()).hexdigest()
        hit = self.cache.get(key)
        if hit:
            self.cached += 1
            return hit[0]
        prompt_price, completion_price = PRICES.get(self.model, UNKNOWN_PRICE)
        reservation = (len(json.dumps(messages)) / 3 * prompt_price + max_tokens * completion_price) / 1e6
        if self.cost + reservation > self.budget:
            raise CandidateError(f"per-evaluation model budget of ${self.budget:.2f} exhausted after {self.requests} requests (${self.cost:.4f} spent)")
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "usage": {"include": True}}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = json.dumps(body).encode()
        last = None
        for attempt in range(4):
            request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=data, headers={
                "Authorization": "Bearer " + self.api_key, "Content-Type": "application/json", "HTTP-Referer": "https://github.com/autoresearch-tasks", "X-Title": "autoresearch-tasks"})
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    payload = json.loads(response.read().decode())
                break
            except urllib.error.HTTPError as error:
                last = f"HTTP {error.code}: {error.read()[:300].decode(errors='replace')}"
                if error.code in (400, 401, 402, 403):
                    raise CandidateError("model request rejected: " + last)
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last = str(error)
            time.sleep(2 * (attempt + 1))
        else:
            raise CandidateError("model request failed after retries: " + str(last))
        if "choices" not in payload or not payload["choices"]:
            raise CandidateError("model returned no choices: " + json.dumps(payload)[:300])
        text = payload["choices"][0].get("message", {}).get("content") or ""
        usage = payload.get("usage") or {}
        cost = float(usage.get("cost") or 0.0)
        if not cost:
            cost = (usage.get("prompt_tokens", 0) * prompt_price + usage.get("completion_tokens", 0) * completion_price) / 1e6
        self.requests += 1
        self.cost += cost
        self.prompt_tokens += int(usage.get("prompt_tokens", 0))
        self.completion_tokens += int(usage.get("completion_tokens", 0))
        self.cache.put(key, self.model, text, cost, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
        return text

    def usage(self):
        return {"model": self.model, "requests": self.requests, "cached_responses": self.cached, "cost_usd": round(self.cost, 6),
                "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens}


# ---------------------------------------------------------------------------
# Answer normalisation and scoring
# ---------------------------------------------------------------------------

def normalize_text(text):
    text = str(text).lower().strip()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = "".join(ch for ch in text if ch not in string.punctuation)
    return " ".join(text.split())


def extract_number(text):
    text = str(text).replace(",", "")
    boxed = re.findall(r"\\boxed\{([^{}]*)\}", text)
    if boxed:
        text = boxed[-1]
    marked = re.findall(r"####\s*(-?\d+(?:\.\d+)?)", text)
    if marked:
        return marked[-1]
    numbers = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", text)
    return numbers[-1] if numbers else None


def numbers_equal(a, b, tol=1e-6):
    try:
        if a is None or b is None:
            return False
        fa = float(eval(str(a), {"__builtins__": {}}, {})) if "/" in str(a) else float(a)  # noqa: S307 - simple fraction
        fb = float(eval(str(b), {"__builtins__": {}}, {})) if "/" in str(b) else float(b)  # noqa: S307
        return abs(fa - fb) <= tol * max(1.0, abs(fb))
    except (ValueError, TypeError, ZeroDivisionError, SyntaxError):
        return False


def extract_choice(text, choices="ABCDEFGHIJ"):
    text = str(text).strip()
    boxed = re.findall(r"\\boxed\{([^{}]*)\}", text)
    if boxed:
        text = boxed[-1]
    patterns = [r"answer\s*(?:is|:)?\s*\(?([%s])\)?" % choices, r"^\(?([%s])\)?[\.\):\s]" % choices, r"\b([%s])\b\s*$" % choices]
    for pattern in patterns:
        found = re.findall(pattern, text, flags=re.I | re.M)
        if found:
            return found[-1].upper()
    letters = re.findall(r"\(([%s])\)" % choices, text)
    return letters[-1].upper() if letters else (text[:1].upper() if text[:1].upper() in choices else None)


def extract_last_line(text):
    lines = [line.strip() for line in str(text).strip().splitlines() if line.strip()]
    if not lines:
        return ""
    last = lines[-1]
    last = re.sub(r"^(final answer|answer)\s*[:\-]\s*", "", last, flags=re.I)
    return last.strip().strip("*").strip()


def f1_score(prediction, truth):
    p, t = normalize_text(prediction).split(), normalize_text(truth).split()
    if not p or not t:
        return float(p == t)
    common = {}
    for token in p:
        if token in t and common.get(token, 0) < t.count(token):
            common[token] = common.get(token, 0) + 1
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision, recall = overlap / len(p), overlap / len(t)
    return 2 * precision * recall / (precision + recall)


def score_answer(kind, prediction, truth):
    """Return 1.0/0.0 (or an F1 in [0,1]) for one item according to the benchmark's answer type."""
    if kind == "number":
        return float(numbers_equal(extract_number(prediction), extract_number(str(truth)) if not isinstance(truth, (int, float)) else truth))
    if kind == "choice":
        return float(extract_choice(prediction) == str(truth).strip().upper()[:1])
    if kind == "exact":
        return float(normalize_text(extract_last_line(prediction)) == normalize_text(truth))
    if kind == "label":
        pred = normalize_text(extract_last_line(prediction))
        options = truth if isinstance(truth, (list, tuple)) else [truth]
        return float(any(normalize_text(option) == pred or normalize_text(option) in pred.split() for option in options))
    if kind == "f1":
        options = truth if isinstance(truth, (list, tuple)) else [truth]
        return max(f1_score(extract_last_line(prediction), option) for option in options)
    if kind == "math":
        def canon(text):
            text = str(text).strip()
            boxed = re.findall(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}", text)
            if boxed:
                text = boxed[-1]
            text = text.replace("\\left", "").replace("\\right", "").replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac").replace("$", "").replace(" ", "").replace("\\!", "")
            text = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
            return text.strip().rstrip(".")
        prediction_canon, truth_canon = canon(prediction), canon(truth)
        if prediction_canon == truth_canon:
            return 1.0
        return float(numbers_equal(extract_number(prediction_canon), extract_number(truth_canon)) and re.fullmatch(r"-?[\d.,/]+", truth_canon) is not None)
    if kind == "contains":
        options = truth if isinstance(truth, (list, tuple)) else [truth]
        pred = normalize_text(prediction)
        return float(any(normalize_text(option) and normalize_text(option) in pred for option in options))
    if kind == "set_f1":
        return set_f1(prediction, truth)
    if kind == "sari":
        return sari_score(truth["source"], prediction, truth["references"])
    if kind == "plan_trip":
        return trip_plan_score(truth["cities"], truth["durations"], prediction)
    raise ValueError(kind)


def _mentions(text):
    parts = re.split(r"[;,\n]|(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", str(text))
    return {normalize_text(x) for x in parts if normalize_text(x)}


def set_f1(prediction, truth):
    """F1 between the set of predicted items (split on ; , or newlines) and the truth list; 1.0 when both are empty."""
    truth_items = {normalize_text(x) for x in (truth if isinstance(truth, (list, tuple)) else [truth]) if normalize_text(x)}
    text = str(prediction).strip()
    if "<eoa>" in text or re.search(r"[\[【](罪名|法条|answer|mentions|labels)[\]】]", text, flags=re.I):
        match = re.search(r"[\[【](?:罪名|法条|answer|mentions|labels)[\]】]\s*[:：]?\s*(.*?)(?:<eoa>|$)", text, flags=re.I | re.S)
        text = match.group(1) if match else text.replace("<eoa>", "")
    else:
        text = extract_last_line(text) if "\n" in text else text
        text = re.sub(r"^\s*(罪名|answer|mentions|labels)\s*[:：]\s*", "", text, flags=re.I)
    text = text.replace("<eoa>", "")
    pred_items = _mentions(text)
    if not truth_items and not pred_items:
        return 1.0
    overlap = len(truth_items & pred_items)
    if overlap == 0:
        return 0.0
    precision, recall = overlap / len(pred_items), overlap / len(truth_items)
    return 2 * precision * recall / (precision + recall)


def sari_score(source, prediction, references):
    """SARI (Xu et al. 2016) for sentence simplification; unigram to 4-gram, averaged."""
    def ngrams(text, n):
        tokens = normalize_text(text).split()
        return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    total = 0.0
    for n in range(1, 5):
        s, o = set(ngrams(source, n)), set(ngrams(prediction, n))
        refs = [set(ngrams(r, n)) for r in references]
        r_all = set().union(*refs) if refs else set()
        # keep
        keep_s = s & o
        keep_ref = s & r_all
        keep_p = len(keep_s & keep_ref) / len(keep_s) if keep_s else (1.0 if not keep_ref else 0.0)
        keep_r = len(keep_s & keep_ref) / len(keep_ref) if keep_ref else 1.0
        keep = 2 * keep_p * keep_r / (keep_p + keep_r) if keep_p + keep_r else 0.0
        # add
        add_o = o - s
        add_ref = r_all - s
        add_p = len(add_o & add_ref) / len(add_o) if add_o else (1.0 if not add_ref else 0.0)
        add_r = len(add_o & add_ref) / len(add_ref) if add_ref else 1.0
        add = 2 * add_p * add_r / (add_p + add_r) if add_p + add_r else 0.0
        # delete (precision only, as in the original definition)
        del_o = s - o
        del_ref = {g for g in s if any(g not in ref for ref in refs)} if refs else set()
        delete = len(del_o & del_ref) / len(del_o) if del_o else (1.0 if not del_ref else 0.0)
        total += (keep + add + delete) / 3
    return total / 4


def parse_trip_plan(response):
    """Port of Natural Plan's trip-planning response parser (google-deepmind/natural-plan, Apache-2.0)."""
    pattern_visit, pattern_flight, pattern_days = r"\d+-\d+", r".*Day (\d+).*from (\w+) to (\w+)", r"European cities for (\d+) days"
    days, flights, flight_days, total_days = [], [], [], None
    for piece in str(response).split("\n"):
        days_match = re.findall(pattern_days, piece)
        if days_match:
            total_days = int(days_match[0])
        visit_match = re.findall(pattern_visit, piece)
        if visit_match:
            days.append(visit_match[0])
            if int(visit_match[0].split("-")[1]) == total_days:
                break
        flight_match = re.findall(pattern_flight, piece)
        if flight_match:
            flights.append(flight_match[0])
    visit_cities, parsed = [], []
    for flight_day, begin_city, end_city in flights:
        flight_days.append(int(flight_day))
        if not visit_cities:
            visit_cities.append(begin_city)
        visit_cities.append(end_city)
    if not days or not flights or not visit_cities:
        return []
    last_day = int(days[-1].split("-")[1])
    flight_days = [1] + flight_days + [last_day]
    for i, city in enumerate(visit_cities):
        if i + 1 >= len(flight_days):
            break
        parsed.append((city, flight_days[i + 1] - flight_days[i] + 1))
    return parsed


def trip_plan_score(cities, durations, response):
    stays = [x for x in str(cities).split("**") if x]
    days = [int(x) for x in str(durations).split("**") if x]
    return float(parse_trip_plan(response) == list(zip(stays, days)))


JUDGE_PROMPT = """You are a strict, consistent evaluator. Rate the RESPONSE to the TASK on a scale from 1 (unacceptable) to 10 (excellent) according to the CRITERIA. Consider correctness, adherence to every constraint in the task, quality of writing and usefulness. Output only the integer rating.

TASK:
{task}

CRITERIA:
{criteria}
{reference}
RESPONSE:
{response}

Rating (1-10):"""


def judge_score(llm, item, answer):
    """Model-as-judge rating in [0, 1] for open-ended items (creative writing, MT-Bench style)."""
    reference = ("\nREFERENCE ANSWER (for guidance):\n" + str(item["answer"]) + "\n") if item.get("answer") else ""
    prompt = JUDGE_PROMPT.format(task=item["question"], criteria=item.get("rubric", "Overall quality."), reference=reference, response=str(answer)[:6000])
    verdict = llm(prompt, max_tokens=8)
    match = re.search(r"\b(10|[1-9])\b", str(verdict))
    if not match:
        return 0.0
    return (int(match.group(1)) - 1) / 9.0


def run_code_tests(code, tests, timeout=10):
    """Execute candidate code plus test assertions in a subprocess; returns True when all pass."""
    import subprocess
    import sys
    import tempfile
    program = code + "\n\n" + tests + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "candidate.py"
        path.write_text(program)
        try:
            proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=timeout, cwd=tmp)
        except subprocess.TimeoutExpired:
            return False
    return proc.returncode == 0


def extract_code(text):
    blocks = re.findall(r"```(?:python)?\n(.*?)```", str(text), flags=re.S)
    return blocks[-1] if blocks else str(text)


# ---------------------------------------------------------------------------
# Benchmark registry (public Hugging Face datasets); filled by benchmark specs
# ---------------------------------------------------------------------------

def _hf(repo, config, split):
    from datasets import load_dataset
    return load_dataset(repo, config, split=split)


def sample_items(spec, n, seed=0):
    """Deterministic sample of ``n`` benchmark items as dicts with question, answer, kind, extra."""
    import random
    key = hashlib.sha256(json.dumps([spec["source"], spec.get("config"), spec.get("split"), n, seed]).encode()).hexdigest()[:16]
    cache = CACHE_DIR / "samples" / f"{spec['id']}-{key}.json"
    if cache.is_file():
        return json.loads(cache.read_text())
    rows = spec["load"]()
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    rng.shuffle(indices)
    items = []
    for index in indices:
        item = spec["item"](rows[index])
        if item is not None:
            items.append(item)
        if len(items) >= n:
            break
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items))
    return items


def benchmark_score(solve, spec, n_samples=None, seed=0, model=None, budget_usd=None):
    """Mean per-item score of ``solve(question, llm) -> answer`` on a fixed sample. Higher is better."""
    llm = LLM(model=model or DEFAULT_MODEL, budget_usd=BUDGET_USD if budget_usd is None else budget_usd)
    items = sample_items(spec, n_samples or SAMPLES, seed)
    require(items, "benchmark sample is empty")
    scores, failures = [], 0
    for item in items:
        try:
            answer = solve(item["question"], llm) if "extra" not in item else solve(item["question"], llm, **item["extra"])
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001 - a crashing scaffold scores zero on that item
            failures += 1
            scores.append(0.0)
            continue
        if item["kind"] == "code":
            scores.append(float(run_code_tests(extract_code(answer), item["answer"])))
        elif item["kind"] == "judge":
            scores.append(judge_score(llm, item, answer))
        else:
            scores.append(score_answer(item["kind"], str(answer), item["answer"]))
    return {"score": float(sum(scores) / len(scores)), "items": len(items), "crashes": failures, "usage": llm.usage()}

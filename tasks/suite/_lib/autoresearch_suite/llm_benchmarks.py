"""Benchmark registry for the model-driven family: public Hugging Face datasets and item adapters.

``spec(name, **options)`` returns a dict with ``id``, ``source``, ``load()``
(returns an indexable dataset split) and ``item(row)`` (returns
``{"question", "answer", "kind"}`` or ``None`` to skip). ``kind`` selects the
scorer in ``llm.score_answer``: ``number``, ``choice``, ``exact``, ``label``,
``f1``, ``contains``, ``math`` or ``code``. Only datasets that are public and
script-free on the Hub are listed; everything else stays documented as
unsupported in the task README.
"""
from __future__ import annotations

from arena_task_paths import data_root

import json
import re
from pathlib import Path

from .runtime import CandidateError

LETTERS = "ABCDEFGHIJKLMNOP"


def _load(repo, config=None, split="test", **kwargs):
    def loader():
        try:
            from datasets import load_dataset
        except ImportError as error:
            raise CandidateError(f"the datasets package is required: {error}") from None
        try:
            return load_dataset(repo, config, split=split, **kwargs)
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"cannot load {repo} ({config}, {split}): {type(error).__name__}: {str(error)[:200]}") from None
    return loader


def _pick(row, *names, default=None):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def _options_text(options):
    if isinstance(options, dict):  # {"label": [...], "text": [...]}
        pairs = zip(options.get("label", LETTERS), options.get("text", []))
    elif isinstance(options, list) and options and isinstance(options[0], dict):
        pairs = [(o.get("key", LETTERS[i]), o.get("value", "")) for i, o in enumerate(options)]
    elif isinstance(options, list):
        pairs = [(LETTERS[i], (str(o).split(")", 1)[1].strip() if re.match(r"^[A-J]\)", str(o)) else str(o))) for i, o in enumerate(options)]
    else:
        return str(options)
    return "\n".join(f"({label}) {text}" for label, text in pairs)


def _choice(question, options, answer, kind="choice"):
    return {"question": question.strip() + "\n\nOptions:\n" + _options_text(options) + "\n\nAnswer with the letter of the correct option.", "answer": answer, "kind": kind}


def _label(text, labels, answer, instruction):
    return {"question": f"{instruction}\nPossible labels: {', '.join(labels)}.\n\nText: {text}\n\nReply with the label only.", "answer": answer, "kind": "label"}


def _math_item(problem, solution_or_answer):
    boxed = re.findall(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}", str(solution_or_answer))
    answer = boxed[-1] if boxed else str(solution_or_answer)
    return {"question": str(problem) + "\n\nGive the final answer inside \\boxed{}.", "answer": answer, "kind": "math"}


BBH_TASKS = ["boolean_expressions", "causal_judgement", "date_understanding", "disambiguation_qa", "dyck_languages", "formal_fallacies", "geometric_shapes", "hyperbaton",
             "logical_deduction_five_objects", "logical_deduction_seven_objects", "logical_deduction_three_objects", "movie_recommendation", "multistep_arithmetic_two", "navigate",
             "object_counting", "penguins_in_a_table", "reasoning_about_colored_objects", "ruin_names", "salient_translation_error_detection", "snarks", "sports_understanding",
             "temporal_sequences", "tracking_shuffled_objects_five_objects", "tracking_shuffled_objects_seven_objects", "tracking_shuffled_objects_three_objects", "web_of_lies", "word_sorting"]
INSTRUCTION_INDUCTION = {"active-passive": "active_to_passive", "antonyms": "antonyms", "cause-effect": "cause_and_effect", "common-concept": "common_concept", "diff": "diff",
                         "first-word-letter": "first_word_letter", "informal-formal": "informal_to_formal", "large-animal": "larger_animal", "letters-list": "letters_list",
                         "negation": "negation", "num-verb": "num_to_verbal", "orthography-starts": "orthography_starts_with", "rhymes": "rhymes", "second-word-letter": "second_word_letter",
                         "sentence-similarity": "sentence_similarity", "sentiment": "sentiment", "singular-plural": "singular_to_plural", "sum": "sum", "synonym": "synonyms",
                         "taxonomy-animal": "taxonomy_animal", "trans-en-de": "translation_en-de", "trans-en-es": "translation_en-es", "trans-en-fr": "translation_en-fr", "word-in-context": "word_in_context"}


def spec(name, **options):  # noqa: C901 - one branch per benchmark
    base = {"id": name, "config": None, "split": None}
    if name == "gsm8k":
        return {**base, "source": "openai/gsm8k", "config": "main", "split": "test", "load": _load("openai/gsm8k", "main", "test"),
                "item": lambda r: {"question": r["question"], "answer": r["answer"].split("####")[-1].strip(), "kind": "number"}}
    if name == "gsm_hard":
        return {**base, "source": "reasoning-machines/gsm-hard", "split": "train", "load": _load("reasoning-machines/gsm-hard", None, "train"),
                "item": lambda r: {"question": r["input"], "answer": r["target"], "kind": "number"}}
    if name == "svamp":
        return {**base, "source": "ChilleD/SVAMP", "split": "test", "load": _load("ChilleD/SVAMP", None, "test"),
                "item": lambda r: {"question": (_pick(r, "question_concat") or (r.get("Body", "") + " " + r.get("Question", ""))).strip(), "answer": _pick(r, "Answer", "answer"), "kind": "number"}}
    if name == "asdiv":
        return {**base, "source": "yimingzhang/asdiv", "split": "test", "load": _load("yimingzhang/asdiv", None, "test"),
                "item": lambda r: {"question": _pick(r, "question", "text", "input"), "answer": _pick(r, "answer", "label", "target"), "kind": "number"}}
    if name == "multiarith":
        return {**base, "source": "ChilleD/MultiArith", "split": "test", "load": _load("ChilleD/MultiArith", None, "test"),
                "item": lambda r: {"question": _pick(r, "question"), "answer": _pick(r, "final_ans", "answer"), "kind": "number"}}
    if name == "mgsm":
        return {**base, "source": "juletxara/mgsm", "config": "en", "split": "test", "load": _load("juletxara/mgsm", "en", "test"),
                "item": lambda r: {"question": r["question"], "answer": r["answer_number"], "kind": "number"}}
    if name == "aqua_rat":
        return {**base, "source": "deepmind/aqua_rat", "config": "raw", "split": "test", "load": _load("deepmind/aqua_rat", "raw", "test"),
                "item": lambda r: _choice(r["question"], r["options"], r["correct"])}
    if name == "commonsense_qa":
        return {**base, "source": "tau/commonsense_qa", "split": "validation", "load": _load("tau/commonsense_qa", None, "validation"),
                "item": lambda r: _choice(r["question"], r["choices"], r["answerKey"])}
    if name == "strategyqa":
        return {**base, "source": "ChilleD/StrategyQA", "split": "test", "load": _load("ChilleD/StrategyQA", None, "test"),
                "item": lambda r: {"question": r["question"] + "\nAnswer yes or no.", "answer": ["yes"] if r["answer"] in (True, "True", "true", 1) else ["no"], "kind": "label"}}
    if name == "drop":
        return {**base, "source": "ucinlp/drop", "split": "validation", "load": _load("ucinlp/drop", None, "validation"),
                "item": lambda r: {"question": "Passage: " + r["passage"] + "\n\nQuestion: " + r["question"], "answer": list(r["answers_spans"]["spans"]), "kind": "f1"}}
    if name == "hotpotqa":
        def item(r):
            context = "\n".join(title + ": " + " ".join(sentences) for title, sentences in zip(r["context"]["title"], r["context"]["sentences"]))
            return {"question": "Context:\n" + context[:6000] + "\n\nQuestion: " + r["question"], "answer": r["answer"], "kind": "f1"}
        return {**base, "source": "hotpotqa/hotpot_qa", "config": "distractor", "split": "validation", "load": _load("hotpotqa/hotpot_qa", "distractor", "validation"), "item": item}
    if name == "mmlu":
        return {**base, "source": "cais/mmlu", "config": "all", "split": "test", "load": _load("cais/mmlu", "all", "test"),
                "item": lambda r: _choice(r["question"], r["choices"], LETTERS[int(r["answer"])])}
    if name == "mmlu_pro":
        category = options.get("category")
        return {**base, "source": "TIGER-Lab/MMLU-Pro", "split": "test", "load": _load("TIGER-Lab/MMLU-Pro", None, "test"),
                "item": lambda r: _choice(r["question"], r["options"], r["answer"]) if not category or str(r.get("category", "")).lower() == category else None}
    if name == "gpqa":
        return {**base, "source": "Idavidrein/gpqa (gated)", "config": "gpqa_diamond", "split": "train", "load": _load("Idavidrein/gpqa", "gpqa_diamond", "train"),
                "item": lambda r: _choice(r["Question"], [r["Correct Answer"], r["Incorrect Answer 1"], r["Incorrect Answer 2"], r["Incorrect Answer 3"]], "A")}
    if name == "math":
        subject = options.get("subject", "algebra")
        level = options.get("level")
        return {**base, "source": "EleutherAI/hendrycks_math", "config": subject, "split": "test", "load": _load("EleutherAI/hendrycks_math", subject, "test"),
                "item": lambda r: _math_item(r["problem"], r["solution"]) if not level or str(r.get("level", "")).endswith(str(level)) else None}
    if name in ("aime24", "aime25", "aime23"):
        repo, split = {"aime24": ("HuggingFaceH4/aime_2024", "train"), "aime25": ("math-ai/aime25", "test"), "aime23": ("AI-MO/aimo-validation-aime", "train")}[name]
        def item(r, name=name):
            if name == "aime23" and "2023" not in str(r.get("url", "")):
                return None
            return {"question": str(_pick(r, "problem", "question")) + "\n\nThe answer is an integer between 0 and 999. Give it inside \\boxed{}.", "answer": str(_pick(r, "answer")), "kind": "number"}
        return {**base, "source": repo, "split": split, "load": _load(repo, None, split), "item": item}
    if name == "livebench_math":
        return {**base, "source": "livebench/math", "split": "test", "load": _load("livebench/math", None, "test"),
                "item": lambda r: {"question": str(_pick(r, "turns", default=[""])[0] if isinstance(_pick(r, "turns"), list) else _pick(r, "question", "turns")), "answer": str(_pick(r, "ground_truth")), "kind": "contains"}}
    if name == "humaneval":
        wanted = options.get("task_id")
        return {**base, "source": "openai/openai_humaneval", "split": "test", "config": wanted, "load": _load("openai/openai_humaneval", None, "test"),
                "item": lambda r: {"question": "Complete the following Python function. Return the complete function in a ```python code block.\n\n" + r["prompt"], "answer": r["test"] + f"\ncheck({r['entry_point']})", "kind": "code"} if not wanted or r["task_id"] == wanted else None}
    if name == "mbpp":
        return {**base, "source": "google-research-datasets/mbpp", "config": "sanitized", "split": "test", "load": _load("google-research-datasets/mbpp", "sanitized", "test"),
                "item": lambda r: {"question": r["prompt"] + "\n\nYour code should pass these tests:\n" + "\n".join(r["test_list"]) + "\nReturn the solution in a ```python code block.", "answer": "\n".join(list(r.get("test_imports", [])) + list(r["test_list"])), "kind": "code"}}
    if name == "bbh":
        task = options["task"]
        return {**base, "source": "lukaemon/bbh", "config": task, "split": "test", "load": _load("lukaemon/bbh", task, "test"),
                "item": lambda r: {"question": r["input"], "answer": r["target"], "kind": "exact"}}
    if name == "instruction_induction":
        task = options["task"]
        path = data_root() / "instruction-induction" / f"{task}.json"

        def load_local(path=path):
            if not path.is_file():
                raise CandidateError(f"Instruction Induction data missing: {path} (download from github.com/orhonovich/instruction-induction data/raw/execute)")
            data = json.loads(path.read_text())
            examples = data["examples"]
            return [examples[k] for k in sorted(examples, key=lambda x: int(x) if str(x).isdigit() else str(x))] if isinstance(examples, dict) else list(examples)

        def item(r):
            if "cause" in r and "effect" in r:  # cause_and_effect: two sentences, pick the cause
                first, second = (r["cause"], r["effect"]) if hash(r["cause"]) % 2 else (r["effect"], r["cause"])
                return {"question": "Task: cause and effect. Which of the two sentences is the cause?\nSentence 1: " + first + "\nSentence 2: " + second + "\nReply with the cause sentence only.", "answer": [r["cause"]], "kind": "contains"}
            if "items" in r and "concept" in r:  # common_concept
                answers = [str(a) for a in (r.get("all_common_concepts") or [r["concept"]])]
                return {"question": "Task: common concept. What do the following have in common?\nItems: " + ", ".join(r["items"]) + "\nReply with a short phrase.", "answer": answers, "kind": "f1"}
            answers = r.get("possible_outputs") or (r.get("output") if "output" in r else r.get("outputs"))
            answers = answers if isinstance(answers, list) else [answers]
            return {"question": "Task: " + task.replace("_", " ") + ". Give the output for the input below.\nInput: " + str(r["input"]), "answer": [str(a) for a in answers], "kind": "label"}
        return {**base, "source": "github.com/orhonovich/instruction-induction (data/raw/execute)", "config": task, "split": "execute", "load": load_local, "item": item}
    if name == "subj":
        return {**base, "source": "SetFit/subj", "split": "test", "load": _load("SetFit/subj", None, "test"),
                "item": lambda r: _label(r["text"], ["subjective", "objective"], r["label_text"], "Classify the sentence as subjective or objective.")}
    if name == "cb":
        names = ["entailment", "contradiction", "neutral"]
        return {**base, "source": "aps/super_glue", "config": "cb", "split": "validation", "load": _load("aps/super_glue", "cb", "validation"),
                "item": lambda r: _label("Premise: " + r["premise"] + "\nHypothesis: " + r["hypothesis"], names, names[int(r["label"])], "Does the premise entail the hypothesis?")}
    if name == "medqa":
        return {**base, "source": "bigbio/med_qa", "config": "med_qa_en_source", "split": "test", "load": _load("bigbio/med_qa", "med_qa_en_source", "test"),
                "item": lambda r: _choice(r["question"], r["options"], str(r["answer_idx"]))}
    if name == "trec":
        names = ["abbreviation", "entities", "description and abstract concepts", "human beings", "locations", "numeric values"]
        return {**base, "source": "SetFit/TREC-QC", "split": "test", "load": _load("SetFit/TREC-QC", None, "test"),
                "item": lambda r: _label(r["text"], names, str(_pick(r, "label_coarse_text", "label_text")).lower(), "Classify the question by the type of answer it asks for.")}
    if name == "ethos":
        return {**base, "source": "SetFit/ethos_binary", "split": "train", "load": _load("SetFit/ethos_binary", None, "train"),
                "item": lambda r: _label(r["text"], ["hate speech", "no hate speech"], "hate speech" if int(r["label"]) == 1 else "no hate speech", "Does the comment contain hate speech?")}
    if name == "sarcasm":
        return {**base, "source": "raquiba/Sarcasm_News_Headline", "split": "train", "load": _load("raquiba/Sarcasm_News_Headline", None, "train"),
                "item": lambda r: _label(r["headline"], ["sarcastic", "not sarcastic"], "sarcastic" if int(r["is_sarcastic"]) == 1 else "not sarcastic", "Is the headline sarcastic?")}
    if name == "liar":
        return {**base, "source": "chengxuphd/liar2", "split": "test", "load": _load("chengxuphd/liar2", None, "test"),
                "item": lambda r: _label(str(_pick(r, "statement")), ["true", "false"], "false" if int(r["label"]) <= 2 else "true", "Is the statement broadly true or false? (pants-on-fire, false and barely-true count as false)")}
    if name == "ag_news":
        names = ["world", "sports", "business", "science and technology"]
        return {**base, "source": "fancyzhx/ag_news", "split": "test", "load": _load("fancyzhx/ag_news", None, "test"),
                "item": lambda r: _label(r["text"], names, names[int(r["label"])], "Classify the news article's topic.")}
    if name == "sst2":
        return {**base, "source": "stanfordnlp/sst2", "split": "validation", "load": _load("stanfordnlp/sst2", None, "validation"),
                "item": lambda r: _label(r["sentence"], ["positive", "negative"], "positive" if int(r["label"]) == 1 else "negative", "Classify the sentiment of the movie review sentence.")}
    if name == "sst5":
        names = ["very negative", "negative", "neutral", "positive", "very positive"]
        return {**base, "source": "SetFit/sst5", "split": "test", "load": _load("SetFit/sst5", None, "test"),
                "item": lambda r: _label(r["text"], names, str(_pick(r, "label_text", default=names[int(r["label"])])), "Classify the sentiment on a five-point scale.")}
    if name in ("cr", "mr"):
        repo = "SetFit/CR" if name == "cr" else "cornell-movie-review-data/rotten_tomatoes"
        return {**base, "source": repo, "split": "test", "load": _load(repo, None, "test"),
                "item": lambda r: _label(str(_pick(r, "text")), ["positive", "negative"], "positive" if int(r["label"]) == 1 else "negative", "Classify the sentiment of the review.")}
    if name == "samsum":
        return {**base, "source": "knkarthick/samsum", "split": "test", "load": _load("knkarthick/samsum", None, "test"),
                "item": lambda r: {"question": "Summarize the following dialogue in one or two sentences.\n\n" + r["dialogue"], "answer": r["summary"], "kind": "f1"}}
    if name == "amazon5":
        names = ["1", "2", "3", "4", "5"]
        return {**base, "source": "SetFit/amazon_reviews_multi_en", "split": "test", "load": _load("SetFit/amazon_reviews_multi_en", None, "test"),
                "item": lambda r: _label(str(_pick(r, "text")), names, str(int(r["label"]) + 1), "Rate the review from 1 (worst) to 5 (best) stars.")}
    if name == "banking77":
        def item(r, names=[]):
            return {"question": "Classify the banking customer query into its intent.\nText: " + r["text"] + "\n\nReply with the intent label only (for example card_arrival).", "answer": str(_pick(r, "label_text", default=r["label"])), "kind": "label"}
        return {**base, "source": "PolyAI/banking77", "split": "test", "load": _load("PolyAI/banking77", None, "test"), "item": item}
    if name == "financial_phrasebank":
        names = ["negative", "neutral", "positive"]
        return {**base, "source": "takala/financial_phrasebank", "config": "sentences_allagree", "split": "train", "load": _load("takala/financial_phrasebank", "sentences_allagree", "train"),
                "item": lambda r: _label(r["sentence"], names, names[int(r["label"])], "Classify the sentiment of the financial news sentence.")}
    if name == "goemotions":
        names = ["admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity", "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief", "joy", "love", "nervousness", "optimism", "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral"]
        return {**base, "source": "google-research-datasets/go_emotions", "config": "simplified", "split": "test", "load": _load("google-research-datasets/go_emotions", "simplified", "test"),
                "item": lambda r: _label(r["text"], names, [names[int(i)] for i in r["labels"]], "Which emotion does the comment express? Reply with one label.")}
    if name == "scicite":
        names = ["method", "background", "result"]
        return {**base, "source": "allenai/scicite", "split": "test", "load": _load("allenai/scicite", None, "test", revision="refs/convert/parquet"),
                "item": lambda r: _label(r["string"], names, names[int(r["label"])], "Classify the intent of the citation sentence.")}
    if name == "scitail":
        return {**base, "source": "allenai/scitail", "config": "tsv_format", "split": "test", "load": _load("allenai/scitail", "tsv_format", "test"),
                "item": lambda r: _label("Premise: " + r["premise"] + "\nHypothesis: " + r["hypothesis"], ["entails", "neutral"], str(r["label"]).lower(), "Does the premise entail the hypothesis?")}
    if name == "symptom2disease":
        return {**base, "source": "gretelai/symptom_to_diagnosis", "split": "test", "load": _load("gretelai/symptom_to_diagnosis", None, "test"),
                "item": lambda r: {"question": "Give the most likely diagnosis for these symptoms, as a short disease name only.\n\n" + str(_pick(r, "input_text", "text")), "answer": str(_pick(r, "output_text", "label")), "kind": "contains"}}
    if name == "tweeteval_hate":
        return {**base, "source": "cardiffnlp/tweet_eval", "config": "hate", "split": "test", "load": _load("cardiffnlp/tweet_eval", "hate", "test"),
                "item": lambda r: _label(r["text"], ["hateful", "not hateful"], "hateful" if int(r["label"]) == 1 else "not hateful", "Is the tweet hateful?")}
    if name == "scone":
        return {**base, "source": "tasksource/scone", "split": "test", "load": _load("tasksource/scone", None, "test"),
                "item": lambda r: _label("Premise: " + str(_pick(r, "sentence1_edited", "sentence1", "premise")) + "\nHypothesis: " + str(_pick(r, "sentence2_edited", "sentence2", "hypothesis")), ["entailment", "neutral"], str(_pick(r, "gold_label_edited", "gold_label", "label")).lower(), "Does the premise entail the hypothesis?")}
    if name == "iris":
        names = ["setosa", "versicolor", "virginica"]
        def item(r):
            features = ", ".join(f"{k}={v}" for k, v in r.items() if k.lower() != "species")
            answer = str(_pick(r, "Species", "species", "label")).lower().replace("iris-", "")
            if options.get("typo"):
                features = features.replace("sepal", "sepl").replace("petal", "petl")
            return {"question": "Classify the iris flower species from its measurements.\n" + features, "answer": answer, "kind": "contains"}
        return {**base, "source": "scikit-learn/iris", "split": "train", "load": _load("scikit-learn/iris", None, "train"), "item": item}
    if name == "sudoku":
        def item(r):
            puzzle = str(_pick(r, "puzzle", "quizzes", "question"))
            solution = str(_pick(r, "solution", "solutions", "answer"))
            if len(puzzle) != 81 or len(solution) != 81:
                return None
            rows = "\n".join(puzzle[i:i + 9].replace("0", ".") for i in range(0, 81, 9))
            return {"question": "Solve this 9x9 Sudoku (dots are blanks). Output the solved grid as 81 digits without spaces on the last line.\n\n" + rows, "answer": solution, "kind": "contains"}
        return {**base, "source": "Ritvik19/Sudoku-Dataset", "split": "train", "load": _load("Ritvik19/Sudoku-Dataset", None, "train"), "item": item}
    if name == "aegis2":
        return {**base, "source": "nvidia/Aegis-AI-Content-Safety-Dataset-2.0", "split": "test", "load": _load("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", None, "test"),
                "item": lambda r: _label(str(_pick(r, "prompt", "text")), ["safe", "unsafe"], str(_pick(r, "prompt_label", "label", "labels_0")).lower(), "Is the user prompt safe or unsafe according to a content-safety policy?")}
    if name in ("nl4opt", "industryor", "mamo_easy", "mamo_complex", "bwor"):
        repo, split = {"nl4opt": ("CardinalOperations/NL4OPT", "test"), "industryor": ("CardinalOperations/IndustryOR", "test"), "mamo_easy": ("CardinalOperations/MAMO", "easy_lp"),
                       "mamo_complex": ("CardinalOperations/MAMO", "complex_lp"), "bwor": ("SJTU/BWOR", "test")}[name]
        return {**base, "source": repo, "split": split, "load": _load(repo, None, split),
                "item": lambda r: {"question": "Solve this operations-research word problem. Formulate the optimisation model and solve it (you may reason briefly, at most about 300 words), then finish with one line of the form 'Answer: <number>' giving the optimal objective value.\n\n" + str(_pick(r, "en_question", "question")),
                                   "answer": str(_pick(r, "en_answer", "answer")), "kind": "number"}}
    if name == "mt_bench":
        category = options.get("category")
        rubric = {"writing": "Creativity, structure, fulfilment of every requirement in the prompt, grammar and engagement.", "roleplay": "Staying in character, consistency with the persona, responsiveness to the prompt, and quality of the dialogue.",
                  "humanities": "Accuracy, depth, balance of perspectives, clarity and completeness."}.get(category, "Helpfulness, relevance, accuracy, depth, creativity and level of detail.")
        return {**base, "source": "HuggingFaceH4/mt_bench_prompts", "split": "train", "load": _load("HuggingFaceH4/mt_bench_prompts", None, "train"),
                "item": lambda r: {"question": str(r["prompt"][0]), "answer": (r.get("reference") or [None])[0], "kind": "judge", "rubric": rubric} if not category or r.get("category") == category else None}
    if name == "creative_writing":
        task = options["task"]
        prompts = CREATIVE_PROMPTS[task]
        return {**base, "source": "local prompts (this repository)", "config": task, "split": "prompts", "load": lambda: [{"prompt": q, "rubric": rubric} for q, rubric in prompts],
                "item": lambda r: {"question": r["prompt"], "answer": None, "kind": "judge", "rubric": r["rubric"]}}
    if name == "epistemic_reasoning":
        return {**base, "source": "tasksource/bigbench", "config": "epistemic_reasoning", "split": "validation", "load": _load("tasksource/bigbench", "epistemic_reasoning", "validation"),
                "item": lambda r: _label(str(r["inputs"]), ["entailment", "non-entailment"], [str(t).strip().lower() for t in r["targets"]], "Does the premise entail the hypothesis? Answer entailment or non-entailment.")}
    if name == "imo_answerbench":
        return {**base, "source": "OpenEvals/IMO-AnswerBench", "split": "train", "load": _load("OpenEvals/IMO-AnswerBench", None, "train"),
                "item": lambda r: {"question": str(r["Problem"]) + "\n\nGive the final answer inside \\boxed{}.", "answer": str(r["Short Answer"]), "kind": "math"}}
    if name == "lawbench_charge":
        url = "https://raw.githubusercontent.com/open-compass/LawBench/e30981bb3ff54c41571f222e0b23e92d27375388/data/zero_shot/3-3.json"
        return {**base, "source": "github.com/open-compass/LawBench data/zero_shot/3-3.json (charge prediction, CAIL2018)", "split": "zero_shot",
                "load": lambda: _github_json(url, "lawbench-3-3.json"),
                "item": lambda r: {"question": r["instruction"] + "\n\n" + r["question"], "answer": [x for x in re.split(r"[;；,，]", str(r["answer"]).split(":", 1)[-1].split("：", 1)[-1]) if x.strip()], "kind": "set_f1"}}
    if name == "natural_plan_trip":
        url = "https://raw.githubusercontent.com/google-deepmind/natural-plan/ca76db336072ff8931db43bc1ca8d381038cf073/data/trip_planning.json"
        return {**base, "source": "github.com/google-deepmind/natural-plan data/trip_planning.json", "split": "all",
                "load": lambda: [v for _, v in sorted(_github_json(url, "natural-plan-trip.json").items())],
                "item": lambda r: {"question": str(r["prompt_5shot"]), "answer": {"cities": r["cities"], "durations": r["durations"]}, "kind": "plan_trip"}}
    if name == "biosses":
        return {**base, "source": "tabilab/biosses", "split": "train", "load": _load("tabilab/biosses", None, "train"),
                "item": lambda r: {"question": "Rate the semantic similarity of the two biomedical sentences on an integer scale from 0 (no relation) to 4 (equivalent). Answer with the integer only.\nSentence 1: " + str(r["sentence1"]) + "\nSentence 2: " + str(r["sentence2"]),
                                   "answer": str(int(round(float(r["score"])))), "kind": "number"}}
    if name == "ncbi_disease":
        def item(r):
            tokens, tags = list(r["tokens"]), list(r["ner_tags"])
            mentions, current = [], []
            for token, tag in zip(tokens, tags):
                if tag == 1:
                    if current:
                        mentions.append(" ".join(current))
                    current = [token]
                elif tag == 2 and current:
                    current.append(token)
                else:
                    if current:
                        mentions.append(" ".join(current))
                    current = []
            if current:
                mentions.append(" ".join(current))
            return {"question": "List every disease or disorder mention in the sentence, separated by semicolons (write 'none' if there is none).\nSentence: " + " ".join(tokens), "answer": mentions or ["none"], "kind": "set_f1"}
        return {**base, "source": "ncbi/ncbi_disease", "split": "test", "load": _load("ncbi/ncbi_disease", None, "test", revision="refs/convert/parquet"), "item": item}
    if name == "asset":
        return {**base, "source": "facebook/asset", "config": "simplification", "split": "test", "load": _load("facebook/asset", "simplification", "test"),
                "item": lambda r: {"question": "Simplify the following sentence so that it is easier to read while keeping its meaning. Output only the simplified sentence.\n\n" + str(r["original"]), "answer": {"source": r["original"], "references": list(r["simplifications"])}, "kind": "sari"}}
    if name == "banking77_mteb":
        return {**base, "source": "mteb/banking77", "split": "test", "load": _load("mteb/banking77", None, "test"),
                "item": lambda r: {"question": "Classify the banking customer query into its intent.\nText: " + str(r["text"]) + "\n\nReply with the intent label only (for example card_arrival).", "answer": str(r["label_text"]), "kind": "label"}}
    if name == "financial_phrasebank_mteb":
        names = ["negative", "neutral", "positive"]
        return {**base, "source": "mteb/financial_phrasebank", "split": "test", "load": _load("mteb/financial_phrasebank", None, "test"),
                "item": lambda r: _label(str(r["text"]), names, names[int(r["label"])], "Classify the sentiment of the financial news sentence.")}
    if name == "heart_disease":
        def item(r):
            features = ", ".join(f"{k}={v}" for k, v in r.items() if k != "target")
            return {"question": "Predict whether the patient has heart disease from these UCI Heart Disease features (cp=chest pain type, trestbps=resting blood pressure, chol=cholesterol, fbs=fasting blood sugar>120, restecg, thalach=max heart rate, exang=exercise angina, oldpeak, slope, ca, thal). Answer yes or no.\n" + features,
                    "answer": ["yes"] if str(r["target"]).strip() not in ("0", "0.0") else ["no"], "kind": "label"}
        return {**base, "source": "skrishna/heart_disease_uci", "split": "test", "load": _load("skrishna/heart_disease_uci", None, "test"), "item": item}
    raise CandidateError(f"unknown benchmark: {name}")


def _github_json(url, name):
    """Download a pinned raw GitHub JSON file once into the LLM cache directory."""
    import urllib.request
    from .llm import CACHE_DIR
    path = CACHE_DIR / "data" / name
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    return json.loads(path.read_text())


_STORY_RUBRIC = "A complete short story (150-400 words) that follows the requested genre and ending, with a coherent plot, vivid but economical prose and no meta commentary."
CREATIVE_PROMPTS = {
    "opinion_writing": [(f"Write a persuasive opinion piece of about 200 words arguing {side} the following statement: {claim}", "A persuasive, well-structured opinion piece of roughly 200 words with a clear position, concrete reasons and a strong close.")
                        for claim in ("cities should ban private cars from their centres", "school homework should be abolished", "remote work makes companies more productive", "space exploration deserves more public funding", "social media does more harm than good")
                        for side in ("for", "against")],
    "poetry": [(f"Write a {genre} poem of 8 to 16 lines with a {tone} tone about {theme}.", f"A poem that is clearly a {genre}, sustains a {tone} tone, has 8-16 lines and uses concrete imagery.")
               for genre, tone, theme in (("haiku sequence", "melancholic", "an empty train station"), ("sonnet", "hopeful", "the first frost"), ("free verse", "angry", "a broken promise"), ("limerick", "playful", "a forgetful robot"),
                                          ("ballad", "mysterious", "a lighthouse keeper"), ("ode", "reverent", "bread"), ("free verse", "tender", "an old photograph"), ("sonnet", "bitter", "a city at night"),
                                          ("haiku sequence", "serene", "rain on a lake"), ("ballad", "triumphant", "a marathon runner"))],
    "stories_ending": [(f"Write a short story (150-400 words) about {premise} with a {ending} ending.", _STORY_RUBRIC) for premise in ("a locksmith who cannot open her own door", "two strangers stuck in an elevator", "a child who finds a map in the attic", "a chef on the last night of a restaurant", "a lighthouse that starts signalling in code")
                       for ending in ("happy", "tragic")],
    "stories_genre": [(f"Write a short story (150-400 words) in the {genre} genre about {premise}.", _STORY_RUBRIC) for genre in ("horror", "romance", "science fiction", "mystery", "comedy")
                      for premise in ("a lost dog", "an inheritance")],
    "stories_genre_ending": [(f"Write a short story (150-400 words) in the {genre} genre about {premise} with a {ending} ending.", _STORY_RUBRIC) for genre, premise, ending in
                             (("horror", "a night shift", "happy"), ("romance", "a bakery", "tragic"), ("science fiction", "a colony ship", "happy"), ("mystery", "a missing violin", "tragic"), ("comedy", "a wedding", "happy"),
                              ("horror", "a lake house", "tragic"), ("romance", "a train journey", "happy"), ("science fiction", "a repair robot", "tragic"), ("mystery", "a locked library", "happy"), ("comedy", "a job interview", "tragic"))],
}

# nq

Adapted RankEvolve lexical retrieval protocol.

Python module exports BM25, Corpus, tokenize and LuceneTokenizer. Corpus(tokenized_documents, ids=corpus_ids); BM25(corpus).rank(query_tokens, top_k=100) returns paired unique integer document indices and finite scores in descending order.

- Full original corpus and all original test queries; sample_queries=0, warmup_queries=0.
- Raw objective is 0.8*Recall@100 + 0.2*binary-nDCG@10 using positive qrels; this is not standard graded BEIR nDCG.
- Search and confirmation use the same test queries: exploratory search-on-test, not held-out generalization evidence.
- Candidate runs in a separate subprocess; grader never imports candidate code and loads qrels after candidate exit. Same UID/container does not guarantee adversarial qrels secrecy.
- Pinned freeform seed uses the original pure-Python tokenizer. Java21/Pyserini belong to a separate baseline path, not this evaluator.
- Prepared data manifest must be reviewed and hash-pinned in dataset-lock.json; unavailable data never becomes a fabricated score.
- No published score or old evaluator baseline is inherited by this adapted protocol.

Prepare the complete dataset with `python -m rankevolve.prepare` using the bundled suite/_lib on PYTHONPATH. Record its reviewed manifest SHA-256 in dataset-lock.json before execution.

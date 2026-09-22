"""Pinned freeform-seed tokenizer closure from ranking-evolved 8f664bcd.

Only byte-preserved stopwords, tokenizer and stemmer definitions are retained.
This is the original pure-Python tokenizer, not a claim of Java Lucene parity.
"""
from __future__ import annotations
import re

LUCENE_STOPWORDS: frozenset[str] = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "if",
        "in",
        "into",
        "is",
        "it",
        "no",
        "not",
        "of",
        "on",
        "or",
        "such",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "was",
        "will",
        "with",
    ]
)

# Extended English stopwords (71 words) - legacy, kept for backwards compatibility
# Includes LUCENE_STOPWORDS plus additional pronouns, auxiliary verbs, etc.
ENGLISH_STOPWORDS: frozenset[str] = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "do",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "out",
        "s",
        "she",
        "so",
        "some",
        "such",
        "t",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "too",
        "us",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    ]
)

class LuceneTokenizer:
    """
    Pure Python implementation of Lucene's DefaultEnglishAnalyzer.

    Replicates the tokenization pipeline used by Pyserini/Anserini:
    1. StandardTokenizer - Unicode-aware word segmentation
    2. EnglishPossessiveFilter - Remove 's and ' suffixes
    3. LowerCaseFilter - Convert to lowercase
    4. StopFilter - Remove common English stopwords
    5. PorterStemFilter - Apply Porter stemming algorithm

    This eliminates the need for Java/Pyserini while producing compatible output.

    Example:
        tokenizer = LuceneTokenizer()
        tokens = tokenizer("The quick brown fox's running")
        # Returns: ['quick', 'brown', 'fox', 'run']
    """

    def __init__(
        self,
        stopwords: frozenset[str] | None = None,
        stem: bool = True,
    ):
        """
        Initialize the tokenizer.

        Args:
            stopwords: Set of stopwords to remove. Defaults to LUCENE_STOPWORDS (33 words).
            stem: Whether to apply Porter stemming. Defaults to True.
        """
        self.stopwords = stopwords if stopwords is not None else LUCENE_STOPWORDS
        self.stem = stem
        self._stemmer = PorterStemmer() if stem else None

    def __call__(self, text: str) -> list[str]:
        """Tokenize text using the Lucene pipeline."""
        # Step 1: StandardTokenizer - extract alphanumeric sequences
        # Also handles contractions and possessives
        tokens = re.findall(r"\w+", text)

        result = []
        for token in tokens:
            # Step 2: EnglishPossessiveFilter - strip possessive endings
            if token.endswith("'s") or token.endswith("'s"):
                token = token[:-2]
            elif token.endswith("'") or token.endswith("'"):
                token = token[:-1]

            # Skip empty tokens
            if not token:
                continue

            # Step 3: LowerCaseFilter
            token = token.lower()

            # Step 4: StopFilter
            if token in self.stopwords:
                continue

            # Step 5: PorterStemFilter
            if self._stemmer is not None:
                token = self._stemmer.stem(token)

            result.append(token)

        return result


class PorterStemmer:
    """
    Porter Stemmer implementation for English.

    Based on the Porter Stemming Algorithm (1980) by Martin Porter.
    Reference: https://tartarus.org/martin/PorterStemmer/

    This is a pure Python implementation that produces the same output as
    Lucene's PorterStemFilter for English text.
    """

    def __init__(self):
        self._vowels = frozenset("aeiou")

    def _is_consonant(self, word: str, i: int) -> bool:
        """Check if character at position i is a consonant."""
        if word[i] in self._vowels:
            return False
        if word[i] == "y":
            return i == 0 or not self._is_consonant(word, i - 1)
        return True

    def _measure(self, word: str) -> int:
        """
        Calculate the measure m of a word.

        m = number of VC (vowel-consonant) sequences in the word.
        """
        n = 0
        i = 0
        length = len(word)

        # Skip initial consonants
        while i < length and self._is_consonant(word, i):
            i += 1

        while i < length:
            # Skip vowels
            while i < length and not self._is_consonant(word, i):
                i += 1
            if i >= length:
                break

            # Count this VC sequence
            n += 1

            # Skip consonants
            while i < length and self._is_consonant(word, i):
                i += 1

        return n

    def _has_vowel(self, word: str) -> bool:
        """Check if word contains a vowel."""
        return any(not self._is_consonant(word, i) for i in range(len(word)))

    def _ends_double_consonant(self, word: str) -> bool:
        """Check if word ends with a double consonant."""
        return len(word) >= 2 and word[-1] == word[-2] and self._is_consonant(word, len(word) - 1)

    def _ends_cvc(self, word: str) -> bool:
        """
        Check if word ends with consonant-vowel-consonant,
        where final consonant is not w, x, or y.
        """
        if len(word) < 3:
            return False
        return (
            self._is_consonant(word, len(word) - 1)
            and not self._is_consonant(word, len(word) - 2)
            and self._is_consonant(word, len(word) - 3)
            and word[-1] not in "wxy"
        )

    def _replace_suffix(
        self, word: str, suffix: str, replacement: str, m_threshold: int = 0
    ) -> str:
        """Replace suffix if word ends with it and measure > threshold."""
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if self._measure(stem) > m_threshold:
                return stem + replacement
        return word

    def stem(self, word: str) -> str:
        """Apply Porter stemming algorithm to word."""
        if len(word) <= 2:
            return word

        word = word.lower()

        # Step 1a: SSES -> SS, IES -> I, SS -> SS, S -> (remove)
        if word.endswith("sses"):
            word = word[:-2]
        elif word.endswith("ies"):
            word = word[:-2]
        elif word.endswith("ss"):
            pass
        elif word.endswith("s"):
            word = word[:-1]

        # Step 1b: (m>0) EED -> EE, (*v*) ED -> , (*v*) ING ->
        if word.endswith("eed"):
            if self._measure(word[:-3]) > 0:
                word = word[:-1]
        elif word.endswith("ed"):
            stem = word[:-2]
            if self._has_vowel(stem):
                word = stem
                # Additional rules after ED removal
                if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
                    word = word + "e"
                elif self._ends_double_consonant(word) and word[-1] not in "lsz":
                    word = word[:-1]
                elif self._measure(word) == 1 and self._ends_cvc(word):
                    word = word + "e"
        elif word.endswith("ing"):
            stem = word[:-3]
            if self._has_vowel(stem):
                word = stem
                # Additional rules after ING removal
                if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
                    word = word + "e"
                elif self._ends_double_consonant(word) and word[-1] not in "lsz":
                    word = word[:-1]
                elif self._measure(word) == 1 and self._ends_cvc(word):
                    word = word + "e"

        # Step 1c: (*v*) Y -> I
        if word.endswith("y") and self._has_vowel(word[:-1]):
            word = word[:-1] + "i"

        # Step 2: Suffix replacements with m > 0
        step2_suffixes = [
            ("ational", "ate"),
            ("tional", "tion"),
            ("enci", "ence"),
            ("anci", "ance"),
            ("izer", "ize"),
            ("abli", "able"),
            ("alli", "al"),
            ("entli", "ent"),
            ("eli", "e"),
            ("ousli", "ous"),
            ("ization", "ize"),
            ("ation", "ate"),
            ("ator", "ate"),
            ("alism", "al"),
            ("iveness", "ive"),
            ("fulness", "ful"),
            ("ousness", "ous"),
            ("aliti", "al"),
            ("iviti", "ive"),
            ("biliti", "ble"),
        ]
        for suffix, replacement in step2_suffixes:
            if word.endswith(suffix):
                stem = word[: -len(suffix)]
                if self._measure(stem) > 0:
                    word = stem + replacement
                break

        # Step 3: Suffix replacements with m > 0
        step3_suffixes = [
            ("icate", "ic"),
            ("ative", ""),
            ("alize", "al"),
            ("iciti", "ic"),
            ("ical", "ic"),
            ("ful", ""),
            ("ness", ""),
        ]
        for suffix, replacement in step3_suffixes:
            if word.endswith(suffix):
                stem = word[: -len(suffix)]
                if self._measure(stem) > 0:
                    word = stem + replacement
                break

        # Step 4: Suffix removal with m > 1
        step4_suffixes = [
            "al",
            "ance",
            "ence",
            "er",
            "ic",
            "able",
            "ible",
            "ant",
            "ement",
            "ment",
            "ent",
            "ion",
            "ou",
            "ism",
            "ate",
            "iti",
            "ous",
            "ive",
            "ize",
        ]
        for suffix in step4_suffixes:
            if word.endswith(suffix):
                stem = word[: -len(suffix)]
                if suffix == "ion":
                    if stem and stem[-1] in "st" and self._measure(stem) > 1:
                        word = stem
                elif self._measure(stem) > 1:
                    word = stem
                break

        # Step 5a: (m>1) E -> , (m=1 and not *o) E ->
        if word.endswith("e"):
            stem = word[:-1]
            m = self._measure(stem)
            if m > 1 or (m == 1 and not self._ends_cvc(stem)):
                word = stem

        # Step 5b: (m>1 and *d and *L) -> single letter
        if self._measure(word) > 1 and self._ends_double_consonant(word) and word.endswith("l"):
            word = word[:-1]

        return word

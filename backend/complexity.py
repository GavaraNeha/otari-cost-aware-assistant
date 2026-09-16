"""
Complexity scoring engine for Otari.

Previous version scored purely on (word_count * 2 + keyword_hits * 15),
which produced unrealistic results: a 40-word rant about pizza would
outscore "Explain recursion". This version scores based on *what kind*
of task is being asked for, using a weighted domain-difficulty
dictionary, with prompt length acting only as a minor secondary signal.

Tiers (approximate):
  0-5    Greetings / small talk
  5-15   Basic factual lookups ("what is X")
  15-25  Conceptual explanations
  25-35  Analysis / summarization
  35-45  Simple code generation (a query, a function, a script)
  45-65  Moderate engineering (APIs, dashboards, CRUD apps)
  65-80  ML / data / pipeline-level work
  80-100 Systems-level / architecture-heavy work (compilers, distributed systems)
"""

import os
import re

# Longer, more specific phrases are listed so they can be matched before
# their shorter substrings (e.g. "distributed database" before "database").
KEYWORD_WEIGHTS = {
    # Tier 0 — greetings / small talk
    "hello": 2, "hi": 2, "hey": 2, "thanks": 2, "thank you": 2,
    "good morning": 2, "good evening": 2, "bye": 2, "goodbye": 2,

    # Tier 1 — basic factual lookups / simple topics
    "what is": 8, "who is": 8, "define": 8, "meaning of": 8,
    "what are": 8, "list of": 10, "python": 12,

    # Tier 2 — conceptual explanations & fundamental CS concepts
    "explain": 15, "describe": 15, "how does": 18, "why does": 18,
    "difference between": 20, "pros and cons": 18,
    "stack": 20, "stacks": 25, "queue": 20, "queues": 25, "tree": 25, "trees": 30,
    "linked list": 30, "linked lists": 30, "heap": 30, "hash table": 35,
    "data structure": 35, "data structures": 38, "recursion": 32, "pointers": 30,

    # Tier 3 — analysis / summarization & intermediate CS
    "summarize": 25, "summary": 25, "tldr": 22, "analyze": 30,
    "compare": 28, "evaluate": 28, "graph": 30, "graphs": 35,
    "sorting algorithm": 40, "search algorithm": 38,

    # Tier 4 — simple code generation & core development
    "sql query": 35, "regex": 35, "write a function": 38,
    "script": 32, "algorithm": 40, "write code": 35, "debug": 34, "fix this bug": 36,
    "api": 35, "flask": 40, "react": 45, "crud": 50,

    # Tier 5 — moderate engineering / full stack
    "crud api": 60, "rest api": 55, "flask app": 55, "dashboard": 55,
    "component": 40, "authentication system": 62,
    "web scraper": 48, "chrome extension": 52, "mobile app": 55,

    # Tier 6 — ML / data / pipeline work
    "unsupervised learning": 70, "supervised learning": 68, "reinforcement learning": 75,
    "machine learning": 70, "neural network": 72, "train a model": 68,
    "data pipeline": 65, "deep learning": 75, "recommendation system": 72,
    "nlp model": 70, "computer vision": 72,

    # Tier 7 — systems-level / architecture-heavy
    "compiler": 90, "distributed compiler": 96, "interpreter": 88, "operating system": 92,
    "distributed database": 95, "distributed system": 93, "architecture": 70,
    "kernel": 90, "consensus algorithm": 95, "blockchain": 85,
    "load balancer": 80, "microservices architecture": 85,
}

# Sort keys longest-first so multi-word phrases are checked before the
# shorter phrases/words they might contain.
_SORTED_KEYWORDS = sorted(KEYWORD_WEIGHTS.keys(), key=len, reverse=True)

# Words that signal the prompt is asking for multiple linked steps
# ("build X and add Y and deploy it") rather than a single task.
_MULTI_STEP_MARKERS = [" and then ", " after that ", " once done ", " followed by ", " using "]


# Pre-compiled word-boundary patterns so short keywords like "hi" or "and"
# only match whole words, not substrings inside longer words.
_KEYWORD_PATTERNS = {
    kw: re.compile(r"\b" + re.escape(kw) + r"\b") for kw in KEYWORD_WEIGHTS
}


def _matched_keywords(prompt_lower: str):
    """Return the list of dictionary keywords found in the prompt."""
    return [kw for kw in _SORTED_KEYWORDS if _KEYWORD_PATTERNS[kw].search(prompt_lower)]


def _multi_step_bonus(prompt_lower: str, word_count: int) -> int:
    """Small bonus for prompts that chain multiple instructions together."""
    marker_hits = sum(1 for m in _MULTI_STEP_MARKERS if m in prompt_lower)
    conjunction_hits = len(re.findall(r"\band\b", prompt_lower))
    if marker_hits or conjunction_hits >= 2:
        return min(15, marker_hits * 5 + max(0, conjunction_hits - 1) * 4)
    return 0


def analyze_complexity(prompt: str):
    prompt_lower = prompt.lower().strip()
    words = prompt.split()
    word_count = len(words)

    if word_count == 0:
        score = 0
    else:
        matches = _matched_keywords(prompt_lower)

        if matches:
            # Highest single keyword weight
            weights = [KEYWORD_WEIGHTS[m] for m in matches]
            max_weight = max(weights)
            
            # Base score = highest keyword weight detected
            base_score = max_weight

            # If prompt combines intent (e.g. explain) with a technical concept (e.g. stacks),
            # give a combo bonus for multiple distinct matches.
            extra_matches = len(matches) - 1
            combo_bonus = min(20, extra_matches * 6)

            length_bonus = min(10, word_count // 5)
            score = base_score + combo_bonus + length_bonus
        else:
            score = min(40, word_count * 3)

        score += _multi_step_bonus(prompt_lower, word_count)
        score = min(100, max(0, score))

    if score < 30:
        return {"level": "simple", "score": score,
                "model": "liquid/lfm-2.5-2.6b:free", "cost": 0.001}
    elif score < 65:
        return {"level": "medium", "score": score,
                "model": "dots-studio/dots-3-note-preview:free", "cost": 0.003}
    else:
        return {"level": "complex", "score": score,
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free", "cost": 0.008}
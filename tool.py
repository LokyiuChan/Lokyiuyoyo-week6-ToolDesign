"""
Custom tool for text analysis: word/sentence statistics and simplified readability.
"""

import re
from typing import Callable, Any


def text_statistics(text: str) -> dict:
    """
    Compute word count, sentence count, averages, and a simplified readability label.

    Args:
        text: The input string to analyze. Must be non-empty after stripping whitespace.

    Returns:
        A JSON-serializable dict. On success:
            - success (bool): True
            - word_count (int): Number of words (whitespace-split tokens).
            - sentence_count (int): Number of sentences (split on . ! ?).
            - avg_word_length (float): Mean characters per word.
            - avg_sentence_length (float): Mean words per sentence.
            - readability_label (str): "Easy", "Medium", or "Hard".
        On failure:
            - success (bool): False
            - error (str): Human-readable error message.
            - error_code (str): Machine-readable code, e.g. "invalid_input", "empty_text".

    Notes:
        - Words are defined as non-empty tokens after splitting on whitespace.
        - Sentences are split on period, exclamation, and question mark; trailing
          punctuation is not required (text with no separators is treated as one sentence).
        - Readability is classified by avg_sentence_length and avg_word_length:
          Easy: short sentences (<=15 words) and short words (<=5 chars).
          Hard: long sentences (>20 words) or long words (>6 chars).
          Medium: otherwise.
        - Edge case: if word_count is 0 (e.g. only punctuation), readability_label
          is set to "Unknown" and averages are 0.0.

    Limitations:
        - No support for abbreviations (e.g. "Dr." may start a new sentence).
        - Readability is a simple heuristic, not a standard index (e.g. not Flesch–Kincaid).
    """
    # Input validation: type
    if not isinstance(text, str):
        return {
            "success": False,
            "error": "Input must be a string.",
            "error_code": "invalid_input",
        }

    # Input validation: empty or whitespace-only
    stripped = text.strip()
    if not stripped:
        return {
            "success": False,
            "error": "Text is empty or contains only whitespace.",
            "error_code": "empty_text",
        }

    # Words: split on whitespace, drop empty
    words = [w for w in stripped.split() if w]
    word_count = len(words)

    # Sentences: split on . ! ? (keep separators so we don't lose boundaries)
    sentence_endings = re.split(r"(?<=[.!?])\s+", stripped)
    # Filter to non-empty; if no separator found, whole text is one sentence
    sentences = [s.strip() for s in sentence_endings if s.strip()]
    if not sentences:
        sentences = [stripped]
    sentence_count = len(sentences)

    # Averages
    avg_word_length = (sum(len(w) for w in words) / word_count) if word_count else 0.0
    avg_sentence_length = (word_count / sentence_count) if sentence_count else 0.0

    # Simplified readability: Easy / Medium / Hard
    if word_count == 0:
        readability_label = "Unknown"
    elif avg_sentence_length <= 15 and avg_word_length <= 5:
        readability_label = "Easy"
    elif avg_sentence_length > 20 or avg_word_length > 6:
        readability_label = "Hard"
    else:
        readability_label = "Medium"

    return {
        "success": True,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "readability_label": readability_label,
    }


class Tool:
    """
    Wrapper for a callable tool with a name, description, and function-calling schema.
    """

    def __init__(self, name: str, description: str, fn: Callable[..., dict]) -> None:
        self.name = name
        self.description = description
        self.fn = fn

    def execute(self, **kwargs: Any) -> dict:
        """
        Run the tool with the given keyword arguments. Returns a structured dict;
        on exception, returns a JSON-serializable error dict instead of raising.
        """
        try:
            return self.fn(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "execution_error",
            }

    def to_dict(self) -> dict:
        """Return a function-calling style schema: name, description, parameters (JSON Schema)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyze for word/sentence statistics and readability.",
                    }
                },
                "required": ["text"],
            },
        }


# Convenience instance for the text_statistics tool
text_statistics_tool = Tool(
    name="text_statistics",
    description="Compute word count, sentence count, average word length, average sentence length, and a simplified readability label (Easy/Medium/Hard) for the given text.",
    fn=text_statistics,
)

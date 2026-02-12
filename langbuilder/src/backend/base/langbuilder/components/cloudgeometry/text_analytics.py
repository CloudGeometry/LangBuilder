"""
CloudGeometry Text Analytics Component

Analyzes text input and returns statistics including word count,
character count, sentence count, reading time estimate, and
most frequent words.
"""

import re
import math
from collections import Counter

from langbuilder.custom import Component
from langbuilder.io import MultilineInput, IntInput, MessageTextInput, Output, BoolInput
from langbuilder.schema import Data
from langbuilder.schema.message import Message


class TextAnalyticsComponent(Component):
    """Analyze text and return statistics like word count, reading time, and top keywords."""

    display_name = "Text Analytics"
    description = "Analyzes text and returns word count, sentence count, reading time, and most frequent words."
    icon = "bar-chart-3"
    name = "TextAnalytics"

    inputs = [
        MultilineInput(
            name="input_text",
            display_name="Input Text",
            info="The text to analyze.",
            required=True,
        ),
        IntInput(
            name="top_n_words",
            display_name="Top N Words",
            info="Number of most frequent words to return.",
            value=10,
            required=False,
        ),
        IntInput(
            name="min_word_length",
            display_name="Min Word Length",
            info="Minimum word length to include in frequency analysis. Words shorter than this are ignored.",
            value=3,
            required=False,
        ),
        BoolInput(
            name="include_reading_time",
            display_name="Include Reading Time",
            info="Whether to calculate estimated reading time.",
            value=True,
            required=False,
        ),
        MessageTextInput(
            name="custom_stop_words",
            display_name="Custom Stop Words",
            info="Comma-separated list of additional stop words to exclude from frequency analysis.",
            value="",
            required=False,
        ),
    ]

    outputs = [
        Output(
            name="analytics_data",
            display_name="Analytics Data",
            method="analyze_text",
        ),
        Output(
            name="summary_message",
            display_name="Summary Message",
            method="build_summary",
        ),
    ]

    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need", "must",
        "it", "its", "this", "that", "these", "those", "i", "you", "he",
        "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
        "his", "our", "their", "what", "which", "who", "whom", "where",
        "when", "how", "not", "no", "nor", "as", "if", "then", "than",
        "too", "very", "just", "about", "above", "after", "again", "all",
        "also", "any", "because", "before", "between", "both", "each",
        "few", "more", "most", "other", "some", "such", "into", "over",
        "own", "same", "so", "up", "out", "only",
    }

    def _get_text(self) -> str:
        raw = self.input_text
        if hasattr(raw, "text"):
            raw = raw.text
        return str(raw)

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", text.lower())
        return words

    def _count_sentences(self, text: str) -> int:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return len(sentences)

    def _count_paragraphs(self, text: str) -> int:
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return len(paragraphs)

    def _get_stop_words(self) -> set:
        stop_words = self.STOP_WORDS.copy()
        custom = self.custom_stop_words
        if hasattr(custom, "text"):
            custom = custom.text
        if custom:
            extras = [w.strip().lower() for w in str(custom).split(",") if w.strip()]
            stop_words.update(extras)
        return stop_words

    def _calculate_reading_time(self, word_count: int) -> dict:
        wpm = 238
        minutes = word_count / wpm
        return {
            "minutes": round(minutes, 1),
            "seconds": round(minutes * 60),
            "display": f"{math.ceil(minutes)} min read",
        }

    def _get_word_frequencies(self, words: list[str]) -> list[dict]:
        stop_words = self._get_stop_words()
        min_len = self.min_word_length or 3
        top_n = self.top_n_words or 10

        filtered = [w for w in words if len(w) >= min_len and w not in stop_words]
        counter = Counter(filtered)
        top_words = counter.most_common(top_n)

        total = len(filtered)
        result = []
        for word, count in top_words:
            result.append({
                "word": word,
                "count": count,
                "percentage": round((count / total) * 100, 2) if total > 0 else 0,
            })
        return result

    def _compute_analytics(self) -> dict:
        text = self._get_text()
        words = self._tokenize(text)
        word_count = len(words)
        char_count = len(text)
        char_no_spaces = len(text.replace(" ", ""))
        sentence_count = self._count_sentences(text)
        paragraph_count = self._count_paragraphs(text)

        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        avg_sentence_length = word_count / sentence_count if sentence_count else 0

        analytics = {
            "word_count": word_count,
            "character_count": char_count,
            "character_count_no_spaces": char_no_spaces,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "average_word_length": round(avg_word_length, 2),
            "average_sentence_length": round(avg_sentence_length, 2),
            "top_words": self._get_word_frequencies(words),
        }

        if self.include_reading_time:
            analytics["reading_time"] = self._calculate_reading_time(word_count)

        return analytics

    def analyze_text(self) -> Data:
        """Return full analytics as a Data object."""
        analytics = self._compute_analytics()
        self.status = f"{analytics['word_count']} words, {analytics['sentence_count']} sentences"
        return Data(data=analytics)

    def build_summary(self) -> Message:
        """Return a human-readable summary message."""
        analytics = self._compute_analytics()

        lines = [
            f"**Text Analytics Summary**",
            f"",
            f"- Words: {analytics['word_count']}",
            f"- Characters: {analytics['character_count']} ({analytics['character_count_no_spaces']} without spaces)",
            f"- Sentences: {analytics['sentence_count']}",
            f"- Paragraphs: {analytics['paragraph_count']}",
            f"- Avg word length: {analytics['average_word_length']} chars",
            f"- Avg sentence length: {analytics['average_sentence_length']} words",
        ]

        if self.include_reading_time and "reading_time" in analytics:
            lines.append(f"- Reading time: {analytics['reading_time']['display']}")

        if analytics["top_words"]:
            lines.append(f"")
            lines.append(f"**Top Words:**")
            for item in analytics["top_words"]:
                lines.append(f"  - \"{item['word']}\" — {item['count']}x ({item['percentage']}%)")

        summary = "\n".join(lines)
        self.status = f"{analytics['word_count']} words analyzed"
        return Message(text=summary)

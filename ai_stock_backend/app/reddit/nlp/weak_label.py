from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

Label = Literal["pos", "neg", "neu"]

_analyzer = SentimentIntensityAnalyzer()

@dataclass(frozen=True)
class WeakLabelResult:
    label: Label
    compound: float  # [-1, 1]

def weak_label(text: str) -> WeakLabelResult:
    scores = _analyzer.polarity_scores(text)
    comp = float(scores["compound"])
    if comp >= 0.05:
        return WeakLabelResult("pos", comp)
    if comp <= -0.05:
        return WeakLabelResult("neg", comp)
    return WeakLabelResult("neu", comp)

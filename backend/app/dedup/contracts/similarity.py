from dataclasses import dataclass

@dataclass(frozen=True)
class SimilarityResult:
    record_a: str
    record_b: str
    decision: str
    score: float
    signals: dict

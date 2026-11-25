from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Mapping, TYPE_CHECKING
import pandas as pd

QualityDimension = Literal["completeness", "consistency", "accuracy", "timeliness", "validity"]

@dataclass(frozen=True)
class FileSource:
    path: Path
    format: Literal["csv", "json"]

@dataclass(frozen=True)
class DatabaseSource:
    pass

@dataclass(frozen=True)
class S3Source:
    pass

@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int
    distinct_count: int
    minimum: float | None = None
    maximum: float | None = None

@dataclass
class ProfileResult:
    row_count: int
    column_count: int
    duplicate_count: int
    columns: list[ColumnProfile]
    quality: "QualityAssessment | None" = None

@dataclass(frozen=True)
class QualityRule:
    """One boolean result per row; null means the check could not be evaluated.

    Evaluators receive the dataset and named trusted reference frames. They
    must preserve the dataset index. Configure freshness cutoffs explicitly
    in timeliness evaluators; no clock or business rules are inferred.
    """

    name: str
    dimension: QualityDimension
    evaluate: Callable[["pd.DataFrame", Mapping[str, "pd.DataFrame"]], "pd.Series"]


@dataclass
class QualityScore:
    passed: int = 0
    evaluated: int = 0
    expected: int = 0

    @property
    def score(self) -> float | None:
        """Proportion passed, on a 0–1 scale; None means unassessed."""
        return self.passed / self.evaluated if self.evaluated else None

    @property
    def coverage(self) -> float | None:
        return self.evaluated / self.expected if self.expected else None


@dataclass
class QualityViolation:
    dimension: QualityDimension
    rule: str
    row_position: int
    message: str
    unevaluated: bool = False


@dataclass
class QualityAssesment:
    dimensions: dict[str, QualityScore]
    weights: dict[str, float]
    overall_score: float | None
    coverage: float
    partial: bool
    violations: list[QualityViolation] = field(default_factory=list)



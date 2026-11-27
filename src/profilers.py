from abc import ABC, abstractmethod
from typing import Generic, Mapping, Sequence, TypeVar
import math
import pandas as pd
from .schemas import ColumnProfile, ProfileResult, QualityAssessment, QualityRule, QualityScore, QualityViolation

T = TypeVar("T")

class Profiler(ABC, Generic[T]):

    @abstractmethod
    def profile(self, data: T) -> ProfileResult:
        """Calculate descriptive statistics for the data."""
        pass

    @abstractmethod
    def score(self, data: T, profile: ProfileResult | None = None) -> QualityAssessment:
        """Score data quality, optionally reusing a profile of the same data."""
        pass

    @abstractmethod
    def assess(self, data: T) -> ProfileResult:
        """Profile and score the data, returning a profile with quality results."""
        pass

class PandasProfiler(Profiler[pd.DataFrame]):

    DIMENSIONS = ("completeness", "consistency", "accuracy", "timeliness", "validity")

    def __init__(self, required_columns: Sequence[str] = (), rules: Sequence[QualityRule] = (), weights: Mapping[str, float] | None = None, reference_data: Mapping[str, pd.DataFrame] | None = None):
        """Configure required fields, quality rules, weights, and references."""
        self.required_columns = tuple(required_columns)
        self.rules = tuple(rules)
        self.weights = dict.fromkeys(self.DIMENSIONS, 1.0)
        if weights is not None:
            if set(weights) - set(self.DIMENSIONS):
                raise ValueError("Unknown quality dimension in weights.")
            self.weights.update(weights)
        if any(not math.isfinite(w) or w < 0 for w in self.weights.values()):
            raise ValueError("Weights must be finite and nonnegative.")
        if not any(self.weights.values()):
            raise ValueError("At least one weight must be positive.")
        if len(set(self.required_columns)) != len(self.required_columns):
            raise ValueError("Required columns must be unique.")
        names = [rule.name for rule in self.rules]
        if len(set(names)) != len(names):
            raise ValueError("Rule names must be unique.")
        for rule in self.rules:
            if rule.dimension not in self.DIMENSIONS:
                raise ValueError(f"Unknown quality dimension: {rule.dimension}")

        self._violations = []
        self.reference_data = dict(reference_data) if reference_data is not None else {}

    def profile(self, data: pd.DataFrame) -> ProfileResult:
        """Calculate null counts, types, ranges, distinct counts, and duplicates."""
        return ProfileResult(
            row_count=len(data),
            column_count=len(data.columns),
            duplicate_count=int(data.duplicated().sum()),
            columns=[self._profile_column(data[column]) for column in data.columns],
        )

    def score(self, data: pd.DataFrame, profile: ProfileResult | None = None) -> QualityAssessment:
        """Calculate dimension and overall scores; profile first if needed."""
        if not data.columns.is_unique:
            raise ValueError("Quality assessment requires unique column names.")
        if profile is None:
            profile = self.profile(data)
        self._violations = []
        scores = {
            "completeness": self._score_completeness(data, profile),
            "consistency": self._score_consistency(data),
            "accuracy": self._score_accuracy(data),
            "timeliness": self._score_timeliness(data),
            "validity": self._score_validity(data),
        }
        active_weight = sum(self.weights.values())
        assessed_weight = sum(self.weights[d] for d, s in scores.items() if s.score is not None)
        overall = (100 * sum(self.weights[d] * s.score for d, s in scores.items()
                             if s.score is not None) / assessed_weight
                   if assessed_weight else None)
        coverage = sum(self.weights[d] * (s.coverage or 0) for d, s in scores.items()) / active_weight
        partial = any(self.weights[d] > 0 and
                      (s.coverage is None or s.evaluated < s.expected)
                      for d, s in scores.items())
        return QualityAssessment(scores, dict(self.weights), overall, coverage, partial, list(self._violations))

    def assess(self, data: pd.DataFrame) -> ProfileResult:
        """Run profile and score once each, attaching quality to the profile."""
        result = self.profile(data)
        result.quality = self.score(data, result)
        return result

    def _profile_column(self, column: pd.Series) -> ColumnProfile:
        """Profile one column, treating nulls and blank strings as missing."""
        blank = column.map(lambda value: isinstance(value, str) and not value.strip())
        missing = column.isna() | blank
        values = column[~missing]
        numeric = pd.api.types.is_numeric_dtype(column) and not values.empty
        return ColumnProfile(
            name=str(column.name),
            dtype=str(column.dtype),
            null_count=int(missing.sum()),
            distinct_count=int(values.nunique()),
            minimum=float(values.min()) if numeric else None,
            maximum=float(values.max()) if numeric else None,
        )

    def _score_completeness(self, data: pd.DataFrame, profile: ProfileResult) -> QualityScore:
        """Measure required values present, including absent columns and blanks."""
        score = self._score_rules(data, "completeness")
        for column in self.required_columns:
            if column not in data:
                present = pd.Series(False, index=data.index, dtype=bool)
            else:
                values = data[column]
                blank = values.map(lambda value: isinstance(value, str) and not value.strip())
                present = values.notna() & ~blank
            self._record(data, score, "completeness", f"required:{column}", present)
        return score

    def _score_consistency(self, data: pd.DataFrame) -> QualityScore:
        """Measure the proportion of evaluated consistency checks passed."""
        return self._score_rules(data, "consistency")

    def _score_accuracy(self, data: pd.DataFrame) -> QualityScore:
        """Measure agreement with the configured trusted references."""
        return self._score_rules(data, "accuracy")

    def _score_timeliness(self, data: pd.DataFrame) -> QualityScore:
        """Measure compliance with explicitly configured freshness rules."""
        return self._score_rules(data, "timeliness")

    def _score_validity(self, data: pd.DataFrame) -> QualityScore:
        """Measure the proportion of evaluated value constraints satisfied."""
        return self._score_rules(data, "validity")

    def _score_rules(self, data: pd.DataFrame, dimension: str) -> QualityScore:
        """Evaluate only the rules configured for the requested dimension."""
        score = QualityScore()
        for rule in self.rules:
            if rule.dimension == dimension:
                self._record(data, score, dimension, rule.name, rule.evaluate(data, self.reference_data))
        return score

    def _record(self, data: pd.DataFrame, score: QualityScore, dimension: str, name: str, outcomes: pd.Series) -> None:
        """Validate rule results and retain failed or unavailable evidence."""
        if not isinstance(outcomes, pd.Series) or not outcomes.index.equals(data.index):
            raise ValueError(f"Rule {name!r} must return a Series with the dataset index.")
        if not pd.api.types.is_bool_dtype(outcomes.dtype):
            raise ValueError(f"Rule {name!r} must return boolean or nullable boolean results.")
        score.expected += len(outcomes)
        score.evaluated += int(outcomes.notna().sum())
        score.passed += int(outcomes.sum())
        for position, value in enumerate(outcomes):
            missing = bool(pd.isna(value))
            if missing or not value:
                self._violations.append(QualityViolation(dimension, name, position, "Check could not be evaluated." if missing else "Check failed.", unevaluated=missing))

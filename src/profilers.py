from abc import ABC, abstractmethod
from typing import Generic, Mapping, Sequence, TypeVar
import pandas as pd
from .schemas import ColumnProfile, ProfileResult, QualityAssessment, QualityRule, QualityScore

T = TypeVar("T")

class Profiler(ABC, Generic[T]):

    @abstractmethod
    def profile(self, data: T) -> ProfileResult:
        """Calculate descriptive statistics for the data."""
        pass

    @abstractmethod
    def score(
        self, data: T, profile: ProfileResult | None = None
    ) -> QualityAssessment:
        """Score data quality, optionally reusing a profile of the same data."""
        pass

    def assess(self, data: T) -> ProfileResult:
        """Profile and score the data, returning a profile with quality results."""
        raise NotImplementedError


class PandasProfiler(Profiler[pd.DataFrame]):

    def __init__(self, required_columns: Sequence[str] = (), rules: Sequence[QualityRule] = (), weights: Mapping[str, float] | None = None, reference_data: Mapping[str, pd.DataFrame] | None = None):
        """Configure required fields, quality rules, weights, and references."""
        self.required_columns = tuple(required_columns)
        self.rules = tuple(rules)
        self.weights = dict(weights) if weights is not None else None
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
        raise NotImplementedError

    def assess(self, data: pd.DataFrame) -> ProfileResult:
        """Run profile and score once each, attaching quality to the profile."""
        raise NotImplementedError

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
        """Measure the proportion of required values present."""
        raise NotImplementedError

    def _score_consistency(self, data: pd.DataFrame) -> QualityScore:
        """Measure the proportion of evaluated consistency checks passed."""
        raise NotImplementedError

    def _score_accuracy(self, data: pd.DataFrame) -> QualityScore:
        """Measure agreement with the configured trusted references."""
        raise NotImplementedError

    def _score_timeliness(self, data: pd.DataFrame) -> QualityScore:
        """Measure compliance with explicitly configured freshness rules."""
        raise NotImplementedError

    def _score_validity(self, data: pd.DataFrame) -> QualityScore:
        """Measure the proportion of evaluated value constraints satisfied."""
        raise NotImplementedError

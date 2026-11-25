from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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

@dataclass
class QualityScore:
    pass

@dataclass
class QualityViolation:
    pass

@dataclass
class QualityAssesment:
    pass

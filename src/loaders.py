from abc import ABC, abstractmethod
from typing import Generic, TypeVar
import pandas as pd
from .schemas import FileSource, DatabaseSource, S3Source

DataSource = FileSource | DatabaseSource | S3Source

T = TypeVar("T")

class DataLoader(ABC, Generic[T]):
    @abstractmethod
    def load(self, source: DataSource) -> T:
        """Load data from the configured source."""
        pass

    @abstractmethod
    def join(self, x: T, y: T, on: str | list[str] | None = None, how: str = "outer", validate: str | None = None) -> T:
        """Combine two datasets using keys or documented row order."""
        pass

class PandasLoader(DataLoader[pd.DataFrame]):
    def load(self, source: FileSource) -> pd.DataFrame:
        """
        Load a csv or a json file into a pandas DataFrame.

        Args:
            source: File source
        Returns:
            A DataFrame containing the file's data.
        Raises:
            ValueError: If the source format is unsupported
        """
        match source.format:
            case "csv":
                return pd.read_csv(source.path)
            case "json":
                return pd.json_normalize(pd.read_json(source.path).to_dict(orient="records"))
            case _:
                raise ValueError(f"Unsupported file format: {source.format}")

    def join(self, x: pd.DataFrame, y: pd.DataFrame, on: str | list[str] | None = None, how: str = "outer", validate: str | None = None, *, left_on: str | list[str] | None = None, right_on: str | list[str] | None = None) -> pd.DataFrame:
        """
        Join DataFrames by column keys or row position. Positional joins require matching row order.

        Args:
            x: Left DataFrame.
            y: Right DataFrame.
            on: Shared join columns; omit all keys to join by row position.
            how: Join type, defaulting to "outer".
            validate: Optional pandas cardinality check.
            left_on: Join columns in x.
            right_on: Join columns in y.
        Returns:
            Joined DataFrame.
        """
        if on is None and left_on is None and right_on is None:
            x = x.reset_index(drop=True).rename_axis("source_row")
            y = y.reset_index(drop=True).rename_axis("source_row")
            return pd.merge(x, y, left_index=True, right_index=True, how=how,
                            suffixes=("_csv", "_json"), indicator=True, validate=validate)
        return pd.merge(x, y, on=on, left_on=left_on, right_on=right_on, how=how, validate=validate)

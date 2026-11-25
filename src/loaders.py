from abc import ABC, abstractmethod
from typing import Generic, TypeVar
import pandas as pd
from .schemas import FileSource, DatabaseSource, S3Source

DataSource = FileSource | DatabaseSource | S3Source

T = TypeVar("T")

class DataLoader(ABC, Generic[T]):
    @abstractmethod
    def load(self, source: DataSource) -> T:
        pass

    @abstractmethod
    def join(self, x: T, y: T, on: str, how: str = "left",
             validate: str | None = None) -> T:
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

    def join(self, x: pd.DataFrame, y: pd.DataFrame, on: str, how: str="left",
             validate: str | None = None) -> pd.DataFrame:
        """
        Join two pandas DataFrames on a shared column.

        Args:
            x: Left DataFrame.
            y: Right DataFrame.
            on: Column to join on.
            how: Join type, defaulting to "left".
            validate: Optional relationship check, such as "many_to_one".
        Returns:
            A DataFrame containing the joined data.
        """
        return pd.merge(x, y, on=on, how=how, validate=validate)

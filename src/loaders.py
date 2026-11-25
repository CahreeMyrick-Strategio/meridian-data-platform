from abc import ABC
from typing import Generic, TypeVar
import pandas as pd
from .schemas import FileSource, DatabaseSource, S3Source

DataSource = FileSource | DatabaseSource | S3Source

T = TypeVar("T")

class DataLoader(ABC, Generic[T]):
    @abstractmethod
    def load(self, source: DataSource) -> T:
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
        pass

    def join(self, x: pd.DataFrame, y: pd.DataFrame, on: str, how: str="left") -> pd.DataFrame:
        """
        Join two pandas DataFrames on a shared column.

        Args:
            x: Left DataFrame.
            y: Right DataFrame.
            on: Column to join on.
            how: Join type, defaulting to "left".
        Returns:
            A DataFrame containing the joined data.
        """
        pass

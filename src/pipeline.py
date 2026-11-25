from typing import Generic, TypeVar

from .loaders import DataLoader, DataSource
from .profilers import Profiler
from .schemas import ProfileResult

T = TypeVar("T")


class ProfilingPipeline(Generic[T]):
    def __init__(self, loader: DataLoader[T], profiler: Profiler[T]):
        self.loader = loader
        self.profiler = profiler
    
    def run(self, source: DataSource) -> ProfileResult:
        data = self.loader.load(source)
        return self.profiler.profile(data)

    def run_joined(self, left: DataSource, right: DataSource, *, on: str, how: str = "left", validate: str | None = None) -> ProfileResult:
        """Load two sources, join them, and profile the joined data."""
        x = self.loader.load(left)
        y = self.loader.load(right)
        data = self.loader.join(x, y, on=on, how=how, validate=validate)
        return self.profiler.profile(data)

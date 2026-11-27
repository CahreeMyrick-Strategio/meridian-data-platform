from typing import Generic, TypeVar
from .loaders import DataLoader
from .profilers import Profiler
from .schemas import FileSource, ProfileResult

T = TypeVar("T")

class ProfilingPipeline(Generic[T]):
    def __init__(self, loader: DataLoader[T], profiler: Profiler[T]):
        """Connect loading, profiling, and optional quality assessment."""
        self.loader = loader
        self.profiler = profiler
    
    def run(self, source: FileSource) -> ProfileResult:
        """Load one source and return its profile and configured assessment."""
        data = self.loader.load(source)
        return self.profiler.assess(data)

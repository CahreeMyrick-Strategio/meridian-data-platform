from pathlib import Path
from src.sources import FileSource
from src.loaders import PandasLoader
from src.profilers import PandasProfiler
from src.pipeline import ProfilingPipeline
from src.reporting import generate_report


def main():

    csv_source = FileSource(path=Path("data/meridian_trades_small.csv"), format="csv")
    json_source = FileSource(path=Path("data/meridian_trades_small.json"), format="json")

    pipeline = ProfilingPipeline(loader=PandasLoader(), profiler=PandasProfiler()) 

    result = pipeline.run(sources=[csv_source, json_source])

    text_report = generate_report(result, format="text")

    print(text_report)


if __name__ == "__main__":
    main()

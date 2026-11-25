from pathlib import Path

from src.schemas import FileSource
from src.loaders import PandasLoader
from src.profilers import PandasProfiler
from src.pipeline import ProfilingPipeline
from src.reporting import generate_report


def main():

    data_dir = Path(__file__).resolve().parent / "data"
    csv_source = FileSource(path=data_dir / "meridian_trades_small.csv", format="csv")
    json_source = FileSource(path=data_dir / "meridian_trades_small.json", format="json")

    pipeline = ProfilingPipeline(PandasLoader(), PandasProfiler())

    for source in (csv_source, json_source):
        result = pipeline.run(source)
        text_report = generate_report(result, format="text")
        print(f"Source: {source.path.name}")
        print(text_report)


if __name__ == "__main__":
    main()

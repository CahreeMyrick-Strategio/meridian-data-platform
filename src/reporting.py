from abc import ABC, abstractmethod
from .schemas import ProfileResult


class ReportGenerator(ABC):

    @abstractmethod
    def generate(self, result: ProfileResult) -> str:
        pass

class TextReportGenerator(ReportGenerator):

    def generate(self, result: ProfileResult) -> str:

        lines = [
            "DATA PROFILING REPORT",
            "=" * 40,
            f"Rows: {result.row_count}",
            f"Columns: {result.column_count}",
            f"Duplicate rows: {result.duplicate_count}",
            ""
        ]

        for column in result.columns:
            lines.extend([
                f"Column: {column.name}",
                f"  Data type: {column.dtype}",
                f"  Null count: {column.null_count}",
                f"  Distinct count: {column.distinct_count}",
                f"  Minimum: {column.minimum}",
                f"  Maximum: {column.maximum}",
                ""
            ])

        return "\n".join(lines)

class MarkdownReportGenerator(ReportGenerator):
    pass

class AIReportGenerator(ReportGenerator):
    pass


def generate_report(result: ProfileResult, format: str = "text") -> str:
    """Select a reporter by format and render a structured profile result.

    Text is currently implemented. Markdown and AI reporting are reserved
    formats until their reporter implementations are available.

    Raises:
        NotImplementedError: If a requested reporter is still a placeholder.
        ValueError: If the format is unknown.
    """
    match format:
        case "text":
            reporter = TextReportGenerator()
        case "markdown" | "ai":
            raise NotImplementedError(f"The {format} reporter is not implemented yet.")
        case _:
            raise ValueError(f"Unsupported report format: {format}. Available formats: 'text'.")

    return reporter.generate(result)

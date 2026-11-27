from abc import ABC, abstractmethod
from .schemas import ProfileResult


class ReportGenerator(ABC):

    @abstractmethod
    def generate(self, result: ProfileResult) -> str:
        """Render a profile for the selected output format."""
        pass

class TextReportGenerator(ReportGenerator):

    def generate(self, result: ProfileResult) -> str:
        """Render descriptive statistics and all five quality dimensions."""
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

        if result.quality is not None:
            quality = result.quality
            lines.append("QUALITY DIMENSIONS")
            overall = "Unassessed" if quality.overall_score is None else f"{quality.overall_score:.2f}/100"
            lines.append(f"Overall: {overall}" + (" (partial)" if quality.partial else ""))
            lines.append(f"Coverage: {quality.coverage:.2%}")
            for dimension, score in quality.dimensions.items():
                value = "Unassessed" if score.score is None else f"{score.score:.2%} ({score.passed}/{score.evaluated})"
                lines.append(f"{dimension.title()}: {value}")
            lines.append(f"Failed checks: {sum(not v.unevaluated for v in quality.violations)}")
            counts = {}
            for violation in quality.violations:
                key = (violation.dimension, violation.rule, violation.unevaluated)
                counts[key] = counts.get(key, 0) + 1
            for (dimension, rule, unavailable), count in counts.items():
                lines.append(f"  {dimension}: {rule}: {count} {'unevaluated' if unavailable else 'failed'}")
        return "\n".join(lines)

def generate_report(result: ProfileResult, format: str = "text") -> str:
    """Select a reporter by format and render a structured profile result.

    Text is the supported report format.

    Raises:
        ValueError: If the format is unknown.
    """
    match format:
        case "text":
            reporter = TextReportGenerator()
        case _:
            raise ValueError(f"Unsupported report format: {format}. Available formats: 'text'.")

    return reporter.generate(result)

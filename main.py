from pathlib import Path
import math
from numbers import Real
import pandas as pd
from src.schemas import FileSource, QualityRule, ProfileResult
from src.loaders import PandasLoader
from src.profilers import Profiler, PandasProfiler
from src.pipeline import ProfilingPipeline
from src.reporting import generate_report


def _column(data: pd.DataFrame, name: str) -> pd.Series:
    """Return a field, or missing values when the field is absent."""
    return data[name] if name in data else pd.Series(pd.NA, index=data.index, dtype="object")


def _is_text(values: pd.Series) -> pd.Series:
    """Require nonblank strings without converting numbers to strings."""
    return values.map(lambda value: isinstance(value, str) and bool(value.strip())).astype(bool)


def _matches_format(values: pd.Series, pattern: str) -> pd.Series:
    """Check original string values against a complete field pattern."""
    return _is_text(values) & values.astype("string").str.fullmatch(pattern).fillna(False)


def _positive_number(values: pd.Series, integer: bool = False) -> pd.Series:
    """Require finite positive numbers, excluding booleans and numeric strings."""
    return values.map(lambda value: isinstance(value, Real) and not isinstance(value, bool)
                      and math.isfinite(value) and value > 0
                      and (not integer or value % 1 == 0)).astype(bool)


def _master_types(reference: pd.DataFrame) -> pd.Series:
    """Build a lookup using only populated, unambiguous master IDs."""
    ids = _column(reference, "instrument_id")
    valid = _is_text(ids) & ~ids.duplicated(keep=False)
    return pd.Series(_column(reference, "instrument_type")[valid].values, index=ids[valid])


def _matches_master(data: pd.DataFrame, instrument_id: str, instrument_type: str, reference: pd.DataFrame) -> pd.Series:
    """Compare types; missing or ambiguous reference evidence is unassessed."""
    ids = _column(data, instrument_id)
    actual = _column(data, instrument_type)
    types = _master_types(reference)
    expected = ids.map(types)
    return actual.astype("string").eq(expected.astype("string")).astype("boolean").mask(
        ~_is_text(ids) | ~_is_text(actual) | ~_is_text(expected), pd.NA).mask(
            _is_text(ids) & ~ids.isin(_column(reference, "instrument_id")), False)


def _parse_dates(values: pd.Series) -> pd.Series:
    """Parse the four documented date formats without guessing month/day order."""
    dates = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    for date_format in ("%Y-%m-%d", "%Y.%m.%d", "%d/%m/%Y", "%m-%d-%Y"):
        dates = dates.fillna(pd.to_datetime(values.where(_is_text(values)), format=date_format, errors="coerce"))
    return dates


def _within_reporting_period(data: pd.DataFrame, trade_date: str) -> pd.Series:
    """Check the assumed historical window; invalid dates fail calendar validity separately."""
    dates = _parse_dates(_column(data, trade_date))
    return dates.between("2025-01-01", "2026-06-30").astype("boolean").mask(dates.isna(), pd.NA)


def _different_participants(data: pd.DataFrame, buyer: str, seller: str) -> pd.Series:
    """Compare populated participant names; missing names cannot be compared."""
    buyers, sellers = _column(data, buyer), _column(data, seller)
    return buyers.astype("string").ne(sellers.astype("string")).astype("boolean").mask(~_is_text(buyers) | ~_is_text(sellers), pd.NA)


def _trade_columns(format: str) -> list[str]:
    """Return the nine corresponding fields in their documented order."""
    if format == "json":
        return ["tradeReference", "security.securityCode", "security.securityType",
                "executionDate", "counterparties.buyingFirm", "counterparties.sellingFirm",
                "tradeDetails.units", "tradeDetails.executionPrice", "tradeDetails.settlementStatus"]
    return ["trade_id", "instrument_id", "instrument_type", "trade_date",
            "buyer", "seller", "quantity", "price", "trade_status"]


def configure_profiler(format: str, reference: pd.DataFrame) -> Profiler[pd.DataFrame]:
    """Configure the five quality dimensions using each export's field names."""
    columns = _trade_columns(format)
    trade_id, instrument_id, instrument_type, trade_date, buyer, seller, quantity, price, status = columns
    rules = [
        QualityRule("trade_id_format", "validity", lambda d, r: _matches_format(_column(d, trade_id), r"TRD-[0-9A-Fa-f]{10}")),
        QualityRule("instrument_id_format", "validity", lambda d, r: _matches_format(_column(d, instrument_id), r"[A-Z]{4}")),
        QualityRule("known_instrument_type", "validity", lambda d, r: _column(d, instrument_type).isin(["Equity", "Bond", "ETF"])),
        QualityRule("buyer_is_text", "validity", lambda d, r: _is_text(_column(d, buyer))),
        QualityRule("seller_is_text", "validity", lambda d, r: _is_text(_column(d, seller))),
        QualityRule("valid_calendar_date", "validity", lambda d, r: _parse_dates(_column(d, trade_date)).notna()),
        QualityRule("instrument_exists_in_master", "validity", lambda d, r: (_is_text(_column(d, instrument_id)) & _column(d, instrument_id).isin(_column(reference, "instrument_id")))),
        QualityRule("unique_trade_id", "consistency", lambda d, r: ~_column(d, trade_id).duplicated(keep=False)),
        QualityRule("unique_trade_row", "consistency", lambda d, r: ~d.reindex(columns=columns).duplicated(keep=False)),
        QualityRule("different_participants", "consistency", lambda d, r: _different_participants(d, buyer, seller)),
        QualityRule("ISO_date_format", "consistency", lambda d, r: _matches_format(_column(d, trade_date), r"\d{4}-\d{2}-\d{2}")),
        QualityRule("instrument_type_matches_master", "accuracy", lambda d, r: _matches_master(d, instrument_id, instrument_type, reference)),
        QualityRule("assumed_reporting_period_2025_01_01_to_2026_06_30", "timeliness", lambda d, r: _within_reporting_period(d, trade_date)),
        QualityRule("positive_finite_price", "validity", lambda d, r: _positive_number(_column(d, price))),
        QualityRule("positive_integer_quantity", "validity", lambda d, r: _positive_number(_column(d, quantity), integer=True)),
        QualityRule("known_status", "validity", lambda d, r: _column(d, status).isin(["EXECUTED", "SETTLED", "CANCELLED", "PENDING", "REJECTED"])),
    ]
    return PandasProfiler(required_columns=columns, rules=rules)


def configure_master_profiler() -> Profiler[pd.DataFrame]:
    """Score populated and unique master keys without aborting trade profiling."""
    return PandasProfiler(required_columns=["instrument_id"], rules=[
        QualityRule("unique_master_id", "consistency", lambda d, r: ~_column(d, "instrument_id").duplicated(keep=False)),
    ], weights={"validity": 0, "accuracy": 0, "timeliness": 0})


def _exports_agree(csv: pd.DataFrame, json: pd.DataFrame) -> pd.Series:
    """Compare all nine values by documented row order, retaining unmatched rows."""
    columns = _trade_columns("csv")
    left = csv.reindex(columns=columns).reset_index(drop=True)
    right = json.reindex(columns=_trade_columns("json")).set_axis(columns, axis=1).reset_index(drop=True)
    size = max(len(left), len(right))
    matches = pd.Series(True, index=range(size))
    for column in columns:
        x, y = left[column].reindex(matches.index), right[column].reindex(matches.index)
        missing_x = x.isna() | x.map(lambda value: isinstance(value, str) and not value.strip())
        missing_y = y.isna() | y.map(lambda value: isinstance(value, str) and not value.strip())
        if column in ("price", "quantity"):
            equal = (pd.to_numeric(x, errors="coerce") - pd.to_numeric(y, errors="coerce")).abs().le(1e-9)
        else:
            equal = x.eq(y).fillna(False)
        matches &= equal | (missing_x & missing_y)
    matches &= (matches.index < len(left)) & (matches.index < len(right))
    if not set(columns).issubset(csv.columns) or not set(_trade_columns("json")).issubset(json.columns):
        matches[:] = False
    return matches


def assess_exports(csv: pd.DataFrame, json: pd.DataFrame) -> ProfileResult:
    """Score row counts and positional agreement once each as dataset constraints."""
    comparison = pd.DataFrame({
        "equal_record_counts": [len(csv) == len(json)],
        "matching_records": [bool(_exports_agree(csv, json).all()) and
                             set(_trade_columns("csv")).issubset(csv.columns) and
                             set(_trade_columns("json")).issubset(json.columns)],
    })
    profiler = PandasProfiler(rules=[
        QualityRule("equal_export_record_counts", "consistency", lambda d, r: d.equal_record_counts),
        QualityRule("matching_export_records", "consistency", lambda d, r: d.matching_records),
    ], weights={"completeness": 0, "validity": 0, "accuracy": 0, "timeliness": 0})
    return profiler.assess(comparison)


def main() -> None:
    """Load each trade export through the pipeline and print its report."""
    
    # data paths
    data_dir = Path(__file__).resolve().parent / "data"
    csv_source = FileSource(path=data_dir / "meridian_trades_small.csv", format="csv")
    json_source = FileSource(path=data_dir / "meridian_trades_small.json", format="json")
    reference_source = FileSource(path=data_dir / "data_info/meridian_reference_data.csv", format="csv")

    # reference data assesment
    loader = PandasLoader()
    try:
        reference = loader.load(reference_source)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not load {reference_source.path.name}: {error}") from error

    print(f"Source: {reference_source.path.name}")
    print(generate_report(configure_master_profiler().assess(reference), format="text"))

    # source data assesment
    for source in (csv_source, json_source):
        try:
            pipeline = ProfilingPipeline(loader, configure_profiler(source.format, reference))
            result = pipeline.run(source)
        except (OSError, ValueError, KeyError) as error:
            raise SystemExit(f"Could not profile {source.path.name}: {error}") from error
        text_report = generate_report(result, format="text")
        print(f"Source: {source.path.name}")
        print(text_report)
        print("Timeliness assumes the historical reporting period 2025-01-01 to 2026-06-30, inclusive.")
        print("Accuracy checks instrument types against the master.")

    try:
        comparison = assess_exports(loader.load(csv_source), loader.load(json_source))
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not compare exports: {error}") from error
    print("Source: CSV/JSON comparison (one dataset-level evaluation per rule)")
    print(generate_report(comparison, format="text"))

if __name__ == "__main__":
    main()

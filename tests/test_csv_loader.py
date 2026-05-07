"""Tests for deeranalysis.utils.csv_loader."""
import io
import base64

import numpy as np
import pandas as pd
import pytest

from deeranalysis.utils.csv_loader import (
    TIME_UNIT_TO_US,
    build_csv_store,
    parse_csv_bytes,
    parse_csv_raw,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CSV_SPACE_SEP = b"0 1.008065\n8 1.024795\n16 0.958489\n24 0.998251\n32 0.981007\n"
CSV_COMMA_SEP = b"t,V_re,V_im\n0,1.0,0.1\n8,0.9,0.2\n16,0.8,0.3\n"
CSV_WITH_HEADER_ROWS = b"# experiment\n# sample\nt,V\n0,1.0\n8,0.9\n"


def _to_dash_b64(data: bytes, mime: str = "text/plain") -> str:
    """Encode bytes as a Dash upload component base64 string."""
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


# ---------------------------------------------------------------------------
# parse_csv_bytes
# ---------------------------------------------------------------------------

class TestParseCsvBytes:
    def test_space_separated_no_header_flag(self):
        # has_header=False → all 5 rows are data, columns named "Column 1", "Column 2"
        df = parse_csv_bytes(CSV_SPACE_SEP, skiprows=0, separator=" ", has_header=False)
        assert df.shape == (5, 2)
        assert list(df.columns) == ["Column 1", "Column 2"]

    def test_space_separated_default_header_consumes_first_row(self):
        # default has_header=True → row 0 becomes column names, 4 data rows remain
        df = parse_csv_bytes(CSV_SPACE_SEP, skiprows=0, separator=" ")
        assert len(df) == 4

    def test_comma_separated_with_header(self):
        df = parse_csv_bytes(CSV_COMMA_SEP, separator=",")
        assert list(df.columns) == ["t", "V_re", "V_im"]
        assert len(df) == 3

    def test_skiprows(self):
        df = parse_csv_bytes(CSV_WITH_HEADER_ROWS, skiprows=2, separator=",")
        assert list(df.columns) == ["t", "V"]
        assert len(df) == 2

    def test_returns_dataframe(self):
        df = parse_csv_bytes(CSV_COMMA_SEP, separator=",")
        assert isinstance(df, pd.DataFrame)

    def test_tab_separator(self):
        data = b"t\tV\n0\t1.0\n8\t0.9\n"
        df = parse_csv_bytes(data, separator="\t")
        assert list(df.columns) == ["t", "V"]


# ---------------------------------------------------------------------------
# parse_csv_raw  (base64 Dash upload format)
# ---------------------------------------------------------------------------

class TestParseCsvRaw:
    def test_roundtrip(self):
        raw = _to_dash_b64(CSV_COMMA_SEP)
        df = parse_csv_raw(raw, separator=",")
        assert list(df.columns) == ["t", "V_re", "V_im"]
        assert len(df) == 3

    def test_with_test_csv_file_no_header(self):
        """test.csv has no header row — all rows must be data."""
        with open("tests/data/test.csv", "rb") as fh:
            raw = _to_dash_b64(fh.read())
        df = parse_csv_raw(raw, separator=" ", has_header=False)
        assert df.shape[1] == 2
        # all values in both columns must be numeric (no string header consumed as data)
        assert pd.to_numeric(df.iloc[:, 0], errors='coerce').notna().all()
        assert pd.to_numeric(df.iloc[:, 1], errors='coerce').notna().all()

    def test_with_test_csv_file_default_header_loses_first_row(self):
        """Confirm that with has_header=True the file loses the first data row."""
        with open("tests/data/test.csv", "rb") as fh:
            raw = _to_dash_b64(fh.read())
        df_with = parse_csv_raw(raw, separator=" ", has_header=True)
        df_without = parse_csv_raw(raw, separator=" ", has_header=False)
        assert len(df_without) == len(df_with) + 1


# ---------------------------------------------------------------------------
# build_csv_store
# ---------------------------------------------------------------------------

class TestBuildCsvStore:
    @pytest.fixture
    def df_comma(self):
        return parse_csv_bytes(CSV_COMMA_SEP, separator=",")

    def test_keys_present(self, df_comma):
        store = build_csv_store(df_comma, t_col="t", vre_col="V_re", vim_col=None, time_unit="ns")
        assert {"RealData", "ImagData", "t", "attrs", "delays", "tmin", "masked_indices"} == set(store)

    def test_t_is_zero_based(self, df_comma):
        store = build_csv_store(df_comma, t_col="t", vre_col="V_re", vim_col=None, time_unit="ns")
        assert store["t"][0] == pytest.approx(0.0)

    def test_tmin_equals_first_point_in_us(self, df_comma):
        # t column is [0, 8, 16] ns → first point = 0 ns = 0.0 µs
        store = build_csv_store(df_comma, t_col="t", vre_col="V_re", vim_col=None, time_unit="ns")
        assert store["tmin"] == pytest.approx(0.0)

    def test_time_unit_conversion_us(self, df_comma):
        store_ns = build_csv_store(df_comma, "t", "V_re", None, time_unit="ns")
        store_us = build_csv_store(df_comma, "t", "V_re", None, time_unit="us")
        # 8 ns → 0.008 µs;  8 µs → 8 µs
        assert store_ns["t"][1] == pytest.approx(8e-3)
        assert store_us["t"][1] == pytest.approx(8.0)

    def test_imaginary_column_used_when_provided(self, df_comma):
        store = build_csv_store(df_comma, "t", "V_re", "V_im", time_unit="us")
        assert store["ImagData"] == pytest.approx([0.1, 0.2, 0.3])

    def test_imaginary_zeros_when_none(self, df_comma):
        store = build_csv_store(df_comma, "t", "V_re", None, time_unit="us")
        assert store["ImagData"] == pytest.approx([0.0, 0.0, 0.0])

    def test_masked_indices_empty(self, df_comma):
        store = build_csv_store(df_comma, "t", "V_re", None, time_unit="us")
        assert store["masked_indices"] == []

    def test_file_format_attr(self, df_comma):
        store = build_csv_store(df_comma, "t", "V_re", None, time_unit="us")
        assert store["attrs"]["file_format"] == "csv"

    def test_missing_column_raises(self, df_comma):
        with pytest.raises(KeyError):
            build_csv_store(df_comma, t_col="nonexistent", vre_col="V_re", vim_col=None, time_unit="us")

    def test_real_file_space_sep(self):
        """End-to-end: parse the headerless test fixture and build a store."""
        with open("tests/data/test.csv", "rb") as fh:
            df = parse_csv_bytes(fh.read(), separator=" ", has_header=False)

        assert list(df.columns) == ["Column 1", "Column 2"]
        store = build_csv_store(df, t_col="Column 1", vre_col="Column 2", vim_col=None, time_unit="ns")

        assert store["t"][0] == pytest.approx(0.0)
        assert len(store["RealData"]) == len(store["t"])
        assert np.isfinite(store["RealData"]).all()


# ---------------------------------------------------------------------------
# TIME_UNIT_TO_US constant
# ---------------------------------------------------------------------------

def test_time_unit_to_us_values():
    assert TIME_UNIT_TO_US["ns"] == pytest.approx(1e-3)
    assert TIME_UNIT_TO_US["us"] == pytest.approx(1.0)
    assert TIME_UNIT_TO_US["ms"] == pytest.approx(1e3)
    assert TIME_UNIT_TO_US["s"]  == pytest.approx(1e6)

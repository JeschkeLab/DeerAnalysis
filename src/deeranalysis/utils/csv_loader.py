"""CSV loading utilities for DeerAnalysis.

Separates pure data-processing logic from Dash callback code so it can be
tested independently of the web framework.
"""
import base64
import io

import numpy as np
import pandas as pd

# Conversion factors from each time unit to microseconds
TIME_UNIT_TO_US: dict[str, float] = {
    'ns': 1e-3,
    'us': 1.0,
    'ms': 1e3,
    's': 1e6,
}


def parse_csv_bytes(
    data: bytes,
    skiprows: int = 0,
    separator: str = ',',
    has_header: bool = True,
) -> pd.DataFrame:
    """Parse CSV data from raw bytes and return a DataFrame.

    When *has_header* is ``False``, columns are named by integer index (0, 1, …)
    and no data row is consumed as a header.
    """
    text = data.decode('utf-8', errors='replace')
    header: int | None = 0 if has_header else None
    df = pd.read_csv(
        io.StringIO(text),
        skiprows=int(skiprows or 0),
        sep=separator,
        header=header,
    )
    if not has_header:
        df.columns = [f"Column {i + 1}" for i in range(len(df.columns))]
    return df


def parse_csv_raw(
    raw_content: str,
    skiprows: int = 0,
    separator: str = ',',
    has_header: bool = True,
) -> pd.DataFrame:
    """Decode a Dash upload base64 string and return a DataFrame."""
    decoded = base64.b64decode(raw_content.split(',')[1])
    return parse_csv_bytes(decoded, skiprows=skiprows, separator=separator, has_header=has_header)


def build_csv_store(
    df: pd.DataFrame,
    t_col: str,
    vre_col: str,
    vim_col: str | None,
    time_unit: str = 'us',
) -> dict:
    """Convert a DataFrame with selected columns into a dataset-store dict.

    Parameters
    ----------
    df:
        DataFrame produced by ``parse_csv_bytes`` / ``parse_csv_raw``.
    t_col:
        Column name for the time axis.
    vre_col:
        Column name for the real signal.
    vim_col:
        Column name for the imaginary signal, or ``None`` if absent.
    time_unit:
        Unit of the time column — one of ``'ns'``, ``'us'``, ``'ms'``, ``'s'``.

    Returns
    -------
    dict
        Dataset store dict compatible with the Dash ``dataset-store`` schema.

    Raises
    ------
    KeyError
        If a requested column is not found in *df*.
    ValueError
        If a column cannot be converted to numeric values.
    """
    scale = TIME_UNIT_TO_US.get(time_unit or 'us', 1.0)
    t_us = pd.to_numeric(df[t_col], errors='raise').to_numpy() * scale
    V_re = pd.to_numeric(df[vre_col], errors='raise').to_numpy()
    V_im = (
        pd.to_numeric(df[vim_col], errors='raise').to_numpy()
        if vim_col
        else np.zeros_like(V_re)
    )

    tmin_us = float(t_us[0])
    t_rel = t_us - t_us[0]  # zero-based time axis stored in the dict

    return {
        'RealData': V_re.tolist(),
        'ImagData': V_im.tolist(),
        't': t_rel.tolist(),
        'attrs': {'title': 'Imported CSV', 'file_format': 'csv'},
        'delays': {},
        'tmin': tmin_us,
        'masked_indices': [],
    }

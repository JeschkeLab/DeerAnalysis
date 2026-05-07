import os
import tempfile

import numpy as np
import pytest

from deeranalysis.utils.io import save_bruker_bes3t
from deeranalysis.utils.eprload import bes3t_eprload


def _load_round_trip(base):
    """Load .DTA/.DSC (and optionally .XGF/.YGF) written by save_bruker_bes3t."""
    with open(base + '.DSC', 'rb') as f:
        dsc = f.read()
    with open(base + '.DTA', 'rb') as f:
        dta = f.read()
    xgf = ygf = None
    if os.path.exists(base + '.XGF'):
        with open(base + '.XGF', 'rb') as f:
            xgf = f.read()
    if os.path.exists(base + '.YGF'):
        with open(base + '.YGF', 'rb') as f:
            ygf = f.read()
    return bes3t_eprload(DSC=dsc, DTA=dta, XGF=xgf, YGF=ygf)


def test_save_bruker_1d_real():
    x = np.linspace(0, 500, 64)
    data = np.sin(x / 50.0)

    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'test_1d_real')
        save_bruker_bes3t(base, x, data)

        assert os.path.exists(base + '.DTA')
        assert os.path.exists(base + '.DSC')

        result = _load_round_trip(base)
        assert result.ndim == 1
        assert len(result) == len(x)
        assert np.allclose(result.values.real, data, rtol=1e-6)


def test_save_bruker_1d_complex():
    x = np.linspace(0, 500, 64)
    data = np.sin(x / 50.0) + 1j * np.cos(x / 50.0)

    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'test_1d_complex')
        save_bruker_bes3t(base, x, data)

        result = _load_round_trip(base)
        assert result.ndim == 1
        assert len(result) == len(x)
        assert np.allclose(result.values, data, rtol=1e-6)


def test_save_bruker_title_and_mwfreq():
    x = np.linspace(0, 100, 32)
    data = np.ones(32)

    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'test_meta')
        save_bruker_bes3t(base, x, data, title='MySample', mw_freq=9.5)

        with open(base + '.DSC') as f:
            dsc_text = f.read()

        assert 'MySample' in dsc_text
        # 9.5 GHz → 9.5e+09 Hz (numpy %g formatting)
        assert 'MWFQ' in dsc_text
        assert '9.5' in dsc_text and '09' in dsc_text


def test_save_bruker_strips_extension():
    x = np.linspace(0, 100, 16)
    data = np.ones(16)

    with tempfile.TemporaryDirectory() as tmp:
        # Pass filename with .DTA extension — should still work
        path_with_ext = os.path.join(tmp, 'test_ext.DTA')
        save_bruker_bes3t(path_with_ext, x, data)

        base = os.path.join(tmp, 'test_ext')
        assert os.path.exists(base + '.DTA')
        assert os.path.exists(base + '.DSC')


def test_save_bruker_nonlinear_axis():
    # Non-uniform spacing triggers .XGF gauge file
    x = np.array([0, 1, 3, 6, 10, 15, 21, 28], dtype=float)
    data = np.ones(len(x))

    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, 'test_nonlinear')
        save_bruker_bes3t(base, x, data)

        assert os.path.exists(base + '.XGF')

        with open(base + '.DSC') as f:
            dsc_text = f.read()
        assert 'IGD' in dsc_text
        assert 'XFMT' in dsc_text

        result = _load_round_trip(base)
        assert len(result) == len(x)
        # The loader applies a hardcoded ns→µs conversion (/1e3) to all axes
        assert np.allclose(result.coords[result.dims[0]].values * 1e3, x)
        assert np.allclose(result.values.real, data, rtol=1e-6)

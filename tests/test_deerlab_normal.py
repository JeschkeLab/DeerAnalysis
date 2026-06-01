"""
Tests for deerlab_fitting and deerlab_background_only.

Coverage:
  Experiment types : 4pDEER, 3pDEER, 5pDEER
  Background models: all models listed in deerlab_options.background_models
                     (phase-shifted variants require complex data and are
                      tested separately)
"""
import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from deeranalysis.utils.deerlab_normal import deerlab_background_only, deerlab_fitting
from deeranalysis.utils.deerlab_options import background_models
from deeranalysis.utils.deerlab_options import fit_to_dict


# ---------------------------------------------------------------------------
# Fitting helpers
# ---------------------------------------------------------------------------

DISTANCE_PARAMS = {
    "mean": 3.0,
    "std": 0.4,
}

EX_input_params = {
    'ex_3pdeer': {'tau': 2.0},
    'ex_4pdeer': {'tau1': 0.4, 'tau2': 3.6},
    'ex_fwd5pdeer': {'tau1': 2, 'tau2': 2, 'tau3': 0.3},
}

def _ex_sim_params(model, overrides=None):
    """Return par0 values for all non-time parameters of a DeerLab bg model."""
    params = {
        name: float(np.atleast_1d(getattr(model, name).par0)[0])
        for name in model.signature
        if name != "t"
    }
    if overrides:
        params.update(overrides)
    return params

def create_deer_dataset(bg_model,exp_name):
# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------
    exp_params = _ex_sim_params(getattr(dl, exp_name))
    t = np.arange(0,)
    r = np.arange(1.5, 4, 0.1)
    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss)
    
    V = Vmodel(**exp_params)

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={"seq_name": "4pDEER", "tau1": tau1_us * 1e3, "tau2": tau2_us * 1e3},
    )


def make_4pdeer_dataset(
    tau1_us=0.5,
    tau2_us=3.5,
    tmin=0.3,
    rmean=4.0,
    rstd=0.4,
    lam=0.3,
    conc=50,
    noise_level=0.02,
    seed=42,
):
    """Single-pathway 4pDEER dataset simulated with the DeerLab dipolar model."""
    t = np.arange(tmin, tau1_us + tau2_us, 0.04)
    r = np.arange(1.5, 8, 0.05)

    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss)
    V = Vmodel(mean=rmean, std=rstd, conc=conc, scale=1.0, mod=lam, reftime=tau1_us)
    V += noise_level * np.random.RandomState(seed).randn(len(t))

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={"seq_name": "4pDEER", "tau1": tau1_us * 1e3, "tau2": tau2_us * 1e3},
    )


def make_3pdeer_dataset(
    tau1_us=2.0,
    tmin=0.3,
    rmean=4.0,
    rstd=0.4,
    lam=0.3,
    conc=50,
    noise_level=0.02,
    seed=42,
):
    """Single-pathway 3pDEER dataset."""
    t = np.arange(tmin, tau1_us, 0.04)
    r = np.arange(1.5, 8, 0.05)

    experiment = dl.ex_3pdeer(tau=tau1_us, pathways=[1])
    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss, experiment=experiment)
    reftime = experiment.reftimes(tau1_us)[0]
    V = Vmodel(mean=rmean, std=rstd, conc=conc, scale=1.0, mod=lam, reftime=reftime)
    V += noise_level * np.random.RandomState(seed).randn(len(t))

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={"seq_name": "3pDEER", "tau1": tau1_us * 1e3},
    )


def make_5pdeer_dataset(
    tau1_us=0.5,
    tau2_us=3.5,
    tau3_us=0.3,
    tmin=0.3,
    rmean=4.0,
    rstd=0.4,
    lam1=0.30,
    lam5=0.10,
    conc=50,
    noise_level=0.02,
    seed=42,
):
    """Two-pathway (1 & 5) 5pDEER dataset using the forward 5pDEER experiment."""
    t = np.arange(tmin, tau1_us + tau2_us + tau3_us, 0.04)
    r = np.arange(1.5, 8, 0.05)

    experiment = dl.ex_fwd5pdeer(tau1_us, tau2_us, tau3_us, pathways=[1, 5])
    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss, experiment=experiment)
    reftime1, reftime5 = experiment.reftimes(tau1_us, tau2_us, tau3_us)
    V = Vmodel(
        mean=rmean, std=rstd, conc=conc, scale=1.0,
        lam1=lam1, reftime1=reftime1,
        lam5=lam5, reftime5=reftime5,
    )
    V += noise_level * np.random.RandomState(seed).randn(len(t))

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={
            "seq_name": "5pDEER",
            "tau1": tau1_us * 1e3,
            "tau2": tau2_us * 1e3,
            "tau3": tau3_us * 1e3,
        },
    )


def make_4pdeer_dataset_with_bg(
    bg_model_name,
    bg_params_override=None,
    tau1_us=0.5,
    tau2_us=3.5,
    tmin=0.3,
    rmean=4.0,
    rstd=0.4,
    noise_level=0.02,
    seed=42,
):
    """4pDEER dataset generated with a specific DeerLab background model."""
    t = np.arange(tmin, tau1_us + tau2_us, 0.04)
    r = np.arange(1.5, 8, 0.05)

    bg_model = getattr(dl, bg_model_name) if bg_model_name != "none" else None
    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss, Bmodel=bg_model)

    # Collect all required parameters from the model, using par0 as defaults
    call_params = {"mean": rmean, "std": rstd, "scale": 1.0}
    for name in Vmodel.signature:
        if name in ("t", "P", "mean", "std", "scale"):
            continue
        call_params[name] = float(np.atleast_1d(getattr(Vmodel, name).par0)[0])

    # Apply any overrides needed for problematic par0 values (e.g. polynomials)
    if bg_params_override:
        call_params.update(bg_params_override)

    V = Vmodel(**call_params)
    V += noise_level * np.random.RandomState(seed).randn(len(t))

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={"seq_name": "4pDEER", "tau1": tau1_us * 1e3, "tau2": tau2_us * 1e3},
    )


def make_bg_only_dataset(
    bg_model_name,
    params_override=None,
    tau1_us=0.4,
    tau2_us=3.6,
    tmin=0.2,
    noise_level=0.005,
    seed=0,
):
    """Background-only dataset generated with a specific DeerLab background model."""
    t = np.arange(tmin, tau1_us + tau2_us, 0.04)
    model = getattr(dl, bg_model_name)
    params = _bg_sim_params(model, params_override)
    V = np.real(model(t, **params))
    V /= V.max()
    V += noise_level * np.random.RandomState(seed).randn(len(t))

    return xr.DataArray(
        data=V,
        coords={"t": t},
        attrs={"seq_name": "4pDEER", "tau1": tau1_us * 1e3, "tau2": tau2_us * 1e3},
    )


# ---------------------------------------------------------------------------
# deerlab_fitting: detailed tests for 4pDEER with bg_hom3d
# ---------------------------------------------------------------------------

class TestDeerlabFitting4pDEER:

    @pytest.fixture(scope="class")
    def fit(self):
        return deerlab_fitting(make_4pdeer_dataset(), compactness=False)

    def test_returns_fit_object(self, fit):
        assert fit is not None

    def test_has_distance_distribution(self, fit):
        assert hasattr(fit, "P")
        assert hasattr(fit, "r")
        assert len(fit.P) == len(fit.r)

    def test_distribution_is_nonnegative(self, fit):
        assert np.all(fit.P >= 0)

    def test_has_modulation_depth(self, fit):
        assert hasattr(fit, "lam")
        assert 0 < fit.lam < 1

    def test_modulation_depth_close_to_true(self, fit):
        assert abs(fit.lam - 0.3) < 0.15

    def test_has_fitted_signal(self, fit):
        assert hasattr(fit, "model")

    def test_vfit_close_to_vexp(self, fit):
        residuals = fit.model - fit.Vexp
        assert np.sqrt(np.mean(residuals**2)) < 0.05

    def test_peak_near_true_distance(self, fit):
        r_peak = fit.r[np.argmax(fit.P)]
        assert abs(r_peak - 4.0) < 1.0

    def test_stats_keys_present(self, fit):
        for key in ("MNR", "SNR", "lam"):
            assert key in fit.stats

    def test_time_axis_attached(self, fit):
        assert hasattr(fit, "t")
        assert len(fit.t) == len(np.arange(0.3, 0.5 + 3.5, 0.04))

    def test_fit_to_dict(self, fit):
        fit_dict = fit_to_dict(fit)
        assert isinstance(fit_dict, dict)
        assert fit_dict['bg_model'] == 'bg_hom3d'
        assert fit_dict['fit_type'] == 'non-parametric'
        assert fit_dict['engine'] == 'DeerLab'
        assert fit_dict['pathways'] == [1]
        assert 'background' in fit_dict and fit_dict['background'] is not None


# ---------------------------------------------------------------------------
# deerlab_fitting: experiment type smoke tests (3pDEER, 5pDEER)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dataset_fn", [
    make_3pdeer_dataset,
    make_5pdeer_dataset,
])
def test_deerlab_fitting_experiment_type(dataset_fn):
    """deerlab_fitting runs and returns expected attributes for each experiment type."""
    fit = deerlab_fitting(dataset_fn(), compactness=False)

    assert fit is not None
    assert hasattr(fit, "P")
    assert hasattr(fit, "r")
    assert hasattr(fit, "lam")
    assert hasattr(fit, "model")
    assert hasattr(fit, "t")
    assert np.all(fit.P >= 0)
    assert 0 < fit.lam < 1
    for key in ("MNR", "SNR", "lam"):
        assert key in fit.stats


# ---------------------------------------------------------------------------
# deerlab_fitting: background model smoke tests
# ---------------------------------------------------------------------------

# Parameter overrides for background models whose par0 values produce
# non-physical (negative) signals over a typical DEER time axis.
_FITTING_BG_OVERRIDES = {
    "bg_poly1": {"p1": -0.05},
    "bg_poly2": {"p1": -0.05, "p2": 0.0},
    "bg_poly3": {"p1": -0.05, "p2": 0.0, "p3": 0.0},
}


# @pytest.mark.parametrize("bg_model_name", _FITTING_BG_MODELS)
# def test_deerlab_fitting_background_model(bg_model_name):
#     """deerlab_fitting runs without error for every supported background model."""
#     bg_model = getattr(dl, bg_model_name, None) if bg_model_name != "none" else None
#     overrides = _FITTING_BG_OVERRIDES.get(bg_model_name)

#     dataset = make_4pdeer_dataset_with_bg(
#         bg_model_name, bg_params_override=overrides
#     )
#     fit = deerlab_fitting(dataset, compactness=False, bg_model=bg_model)

#     assert fit is not None
#     assert hasattr(fit, "P")
#     assert hasattr(fit, "r")
#     assert hasattr(fit, "lam")
#     assert hasattr(fit, "model")
#     assert np.all(fit.P >= 0)
#     assert 0 < fit.lam < 1


# ---------------------------------------------------------------------------
# Background-only fitting tests
# ---------------------------------------------------------------------------

BG_MODELS = [model['value'] for model in background_models]
BG_MODELS.remove('none')

def _bg_sim_params(model, overrides=None):
    """Return par0 values for all non-time parameters of a DeerLab bg model."""
    params = {
        name: float(np.atleast_1d(getattr(model, name).par0)[0])
        for name in model.signature
        if name != "t"
    }
    if overrides:
        params.update(overrides)
    return params

@pytest.mark.parametrize("bg_model_name", BG_MODELS)
def test_deerlab_background_only_model(bg_model_name):
    """deerlab_background_only runs and produces a valid fit for each bg model."""
    dataset = make_bg_only_dataset(bg_model_name)
    bg_model = getattr(dl, bg_model_name)

    fit = deerlab_background_only(dataset, bg_model=bg_model)

    assert fit is not None
    assert hasattr(fit, "model")
    assert hasattr(fit, "Vexp")
    assert hasattr(fit, "t")
    assert hasattr(fit, "Bmodel")

    residuals = fit.model - fit.Vexp
    assert np.sqrt(np.mean(residuals**2)) < 0.1



class TestDeerlabFittingBackgroundOnly:

    @pytest.fixture(scope="class")
    def fit(self):
        return deerlab_background_only(make_bg_only_dataset("bg_hom3d"), bg_model=dl.bg_hom3d)

    def test_returns_fit_object(self, fit):
        assert fit is not None

    def test_has_fitted_signal(self, fit):
        assert hasattr(fit, "model")

    def test_vfit_close_to_vexp(self, fit):
        residuals = fit.model - fit.Vexp
        assert np.sqrt(np.mean(residuals**2)) < 0.1

    def test_fit_to_dict(self, fit):
        fit_dict = fit_to_dict(fit, background_only=True)
        assert isinstance(fit_dict, dict)
        assert fit_dict['bg_model'] == 'bg_hom3d'
        assert fit_dict['fit_type'] == 'background'
        assert fit_dict['engine'] == 'DeerLab'
        assert fit_dict['pathways'] is None
        assert 'background' in fit_dict and fit_dict['background'] is not None
        assert 'model' in fit_dict and fit_dict['model'] is None
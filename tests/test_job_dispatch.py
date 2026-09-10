"""End-to-end test for one job_dispatch handler: builds a Dataset row in a temp DB, queues
params the way pages/nonparametric.py's queue_fit callback would, and checks the handler
returns a result dict shaped like what the page's fit-results-store expects."""
import tempfile

import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from deeranalysis.utils import database as db
from deeranalysis.utils.database import Dataset, Fit
from deeranalysis.utils.job_dispatch import run_nonparametric_fit_job, save_fit_from_job
from deeranalysis.utils.job_tracking import create_job, get_job


def make_4pdeer_dataset(tau1_us=0.5, tau2_us=3.5, tmin=0.3, rmean=4.0, rstd=0.4,
                         lam=0.3, conc=50, noise_level=0.02, seed=42):
    t = np.arange(tmin, tau1_us + tau2_us, 0.04)
    r = np.arange(1.5, 8, 0.05)
    Vmodel = dl.dipolarmodel(t, r, Pmodel=dl.dd_gauss)
    V = Vmodel(mean=rmean, std=rstd, conc=conc, scale=1.0, mod=lam, reftime=tau1_us)
    V += noise_level * np.random.RandomState(seed).randn(len(t))
    return xr.DataArray(V, coords={"t": t},
                         attrs={"seq_name": "4pDEER", "tau1": tau1_us * 1e3, "tau2": tau2_us * 1e3})


@pytest.fixture()
def dataset_id():
    with tempfile.TemporaryDirectory() as tmp:
        db.init_db(tmp)
        session = db.get_session()
        ds = make_4pdeer_dataset()
        entry = Dataset(
            name="job-dispatch-test", project="p", sample="s",
            t=ds.t.values.tolist(), V=ds.values.real.tolist(), V_im=[0.0] * len(ds.t),
            exp="4pDEER", delays={"tau1": 500.0, "tau2": 3500.0, "deadtime": 0.0}, meta={},
        )
        session.add(entry)
        session.commit()
        yield entry.id
        session.close()
        db.engine = None
        db.Session = None


def test_run_nonparametric_fit_job(dataset_id):
    params = {
        "dataset_id": dataset_id,
        "bg_model_option": "bg_hom3d",
        "compactness": False,
        "distance_axis": [1.5, 8.0],
        "pathways_options": ["1"],
        "adv_options": {"regparam": "bic", "regparamrange": [1e-8, 1e2]},
        "model_params": None,
        "bootstrap_enabled": False,
        "bootstrap_samples": 250,
    }
    result = run_nonparametric_fit_job(params)

    assert result["engine"] == "DeerLab"
    assert result["fit_type"] == "Non-Parametric"
    assert isinstance(result["t"], list)
    assert isinstance(result["model"], list)
    assert isinstance(result["P_model"], list)
    assert isinstance(result["r"], list)
    assert "data" in result and isinstance(result["data"], str)
    assert "dist_stats" in result
    assert "gof" in result


def test_run_nonparametric_fit_job_no_pathways_or_bg_raises(dataset_id):
    params = {
        "dataset_id": dataset_id,
        "bg_model_option": "none",
        "distance_axis": [1.5, 8.0],
        "pathways_options": [],
    }
    with pytest.raises(ValueError):
        run_nonparametric_fit_job(params)


def test_save_fit_from_job_creates_fit_row(dataset_id):
    params = {
        "dataset_id": dataset_id,
        "bg_model_option": "bg_hom3d",
        "compactness": False,
        "distance_axis": [1.5, 8.0],
        "pathways_options": ["1"],
        "adv_options": {"regparam": "bic", "regparamrange": [1e-8, 1e2]},
        "model_params": None,
        "bootstrap_enabled": False,
        "bootstrap_samples": 250,
    }
    result = run_nonparametric_fit_job(params)
    job_id = create_job("non-parametric_fit", page="non-parametric", label="job-dispatch-test", params=params)
    job = get_job(job_id)

    save_fit_from_job(job, result)

    session = db.get_session()
    fits = session.query(Fit).filter_by(dataset_id=dataset_id).all()
    assert len(fits) == 1
    assert fits[0].engine == "DeerLab"
    assert fits[0].fit_type == "Non-Parametric"
    session.close()

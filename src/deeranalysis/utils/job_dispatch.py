"""Maps a Job's job_type to a handler that performs the actual (potentially long-running) fit.

Each handler takes the JSON-serializable ``params`` dict stored on the Job row and returns a
JSON-serializable result dict, in the same shape the corresponding page's ``run_fit`` callback
used to build for its ``fit-results-store`` / ``fit-results-store-multi``. This factors the
"build kwargs -> call fit function -> serialize result" logic that used to run inline inside
each page's Dash callback, so it can be executed from the background job dispatcher instead.
"""
import os
import numpy as np
import deerlab as dl

from deeranalysis.utils.database import get_session, Dataset, Fit, fit_global_datasets, fit_siblings
from deeranalysis.utils import dataarray_from_database_entry
from deeranalysis.utils.deerlab_normal import deerlab_fitting, deerlab_background_only
from deeranalysis.utils.deerlab_global import deerlab_global_fitting
from deeranalysis.utils.deerlab_population import deerlab_population_fitting, determine_pop_P
from deeranalysis.utils.deerlab_options import fit_to_dict, dists_stats_to_list, name_dataset_from_dict
from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict
from deeranalysis.utils.deernet import deernet2
from deeranalysis.components.setup_modal_desktop import get_DeerAnalysis_directory
from deeranalysis.utils.job_tracking import to_jsonable

# job_type -> whether its params carry a single "dataset_id" or a list "dataset_ids"
MULTI_DATASET_JOB_TYPES = {"population_fit", "global_fit"}


def _load_dataset(dataset_id):
    session = get_session()
    entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    mask = np.array(entry.mask) if entry.mask else None
    session.close()
    return dataset, mask


def _load_datasets(dataset_ids):
    session = get_session()
    datasets = []
    for ds_id in dataset_ids:
        entry = session.query(Dataset).filter_by(id=ds_id).first()
        ds = dataarray_from_database_entry(entry)
        datasets.append(ds.assign_coords(t=ds.t.values))
    session.close()
    return datasets


def _bootstrap_kwargs(params):
    if params.get("bootstrap_enabled") and params.get("bootstrap_samples"):
        return {"bootstrap": int(params["bootstrap_samples"]), "bootcores": min(4, os.cpu_count() or 1)}
    return {}


def run_nonparametric_fit_job(params):
    dataset, mask = _load_dataset(params["dataset_id"])
    distance_axis = params["distance_axis"]
    r = np.linspace(distance_axis[0], distance_axis[1], 100)
    bg_model_option = params.get("bg_model_option")
    bg_model = getattr(dl, bg_model_option, dl.bg_hom3d) if bg_model_option != "none" else None
    pathways = [int(p) for p in (params.get("pathways_options") or [])]
    adv_options = params.get("adv_options") or {}
    model_params = params.get("model_params")

    if len(pathways) == 0:
        if bg_model is None:
            raise ValueError("Please select at least one pathway or a background model.")
        fit = deerlab_background_only(dataset, bg_model=bg_model, model_overrides=model_params, mask=mask, **_bootstrap_kwargs(params))
        fit.background = fit.model
        fit_dict = fit_to_dict(fit, background_only=True)
        fit_dict["fit_type"] = "background"
        fit_dict["dist_stats"] = {}
        fit_dict["gof"] = fit.stats
        # A background-only fit is made with the background model itself
        fit_dict["warnings"] = warnings_to_dict(check_fit_results(fit, bg_model))
        return fit_dict

    fit = deerlab_fitting(dataset, compactness=params.get("compactness", False), model=None, ROI=False,
                           bg_model=bg_model, r=r, pathways=pathways, model_overrides=model_params, mask=mask,
                           **adv_options, **_bootstrap_kwargs(params))
    dist_stats = dl.diststats(r, fit.P, fit.PUncert)
    fit_dict = fit_to_dict(fit)
    fit_dict["dist_stats"] = dists_stats_to_list(*dist_stats)
    fit_dict["gof"] = fit.stats
    fit_dict["warnings"] = warnings_to_dict(check_fit_results(fit, fit.Vmodel))
    return fit_dict


def run_parametric_fit_job(params):
    dataset, mask = _load_dataset(params["dataset_id"])
    fit_options = params.get("fit_options") or {}
    distance_axis = fit_options.get("distance_axis", [2, 6])
    r = np.linspace(distance_axis[0], distance_axis[1], 100)
    Bmodel = getattr(dl, fit_options.get("bg_model", "bg_hom3d"), dl.bg_hom3d)
    Pmodel = getattr(dl, fit_options.get("dist_model", "dd_gauss"), dl.dd_gauss)
    pathways = [int(p) for p in fit_options.get("pathways_options", ["1"])]
    model_params = params.get("model_params")

    fit = deerlab_fitting(dataset, compactness=False, model=Pmodel, ROI=False, bg_model=Bmodel, r=r,
                           pathways=pathways, multistart=fit_options.get("multistart", 1),
                           model_overrides=model_params, mask=mask, **_bootstrap_kwargs(params))
    r = fit.r
    dist_stats = dl.diststats(r, fit.P, fit.PUncert)
    fit_dict = fit_to_dict(fit)
    fit_dict["dist_stats"] = dists_stats_to_list(*dist_stats)
    fit_dict["gof"] = fit.stats
    fit_dict["warnings"] = warnings_to_dict(check_fit_results(fit, fit.Vmodel))
    return fit_dict


def run_background_fit_job(params):
    dataset, mask = _load_dataset(params["dataset_id"])
    fit_options = params.get("fit_options") or {}
    Bmodel = getattr(dl, fit_options.get("bg_model", "bg_hom3d"), dl.bg_hom3d)
    model_params = params.get("model_params")

    fit = deerlab_background_only(dataset, bg_model=Bmodel, mask=mask, model_overrides=model_params, **_bootstrap_kwargs(params))
    fit_dict = fit_to_dict(fit, background_only=True)
    fit_dict["gof"] = fit.stats
    fit_dict["warnings"] = warnings_to_dict(check_fit_results(fit, Bmodel))
    return fit_dict


def _calc_population_fractions(fit):
    n_datasets = len(fit.Vexp)
    n_pops = fit.n_pops
    output = []
    for i in range(n_datasets):
        populations = {}
        for j in range(n_pops - 1):
            letter = chr(ord("A") + j)
            frac = getattr(fit, f"frac{letter}_{i+1}")
            frac_unc = getattr(fit, f"frac{letter}_{i+1}Uncert")
            ci = frac_unc.ci(95)
            unc = (ci[1] - ci[0]) / 2
            populations[letter] = {"frac": frac, "unc": unc}
        output.append(populations)
        last_letter = chr(ord("A") + n_pops - 1)
        last_frac = 1 - sum(populations[chr(ord("A") + j)]["frac"] for j in range(n_pops - 1))
        last_unc = np.sqrt(sum(populations[chr(ord("A") + j)]["unc"] ** 2 for j in range(n_pops - 1)))
        output[-1][last_letter] = {"frac": last_frac, "unc": last_unc}
    return output


def _population_fit_to_dict(fit, n_datasets):
    Prs, PUQs = determine_pop_P(fit.r, fit, fit.Pmodel, n_datasets, fit.n_pops)
    fit.P = Prs
    fit.PUncert = PUQs
    output = {
        "engine": "DeerLab",
        "fit_type": "Population",
        "bg_model": fit.bg_model.name if fit.bg_model else None,
        "dist_model": fit.Pmodel.name if hasattr(fit, "Pmodel") else None,
        "n_pops": fit.n_pops if hasattr(fit, "n_pops") else None,
        "pathways": fit.pathways[0] if hasattr(fit, "pathways") and fit.pathways else [],
        "r": fit.r.tolist() if fit.r is not None else None,
        "model_description": fit.__str__() if fit is not None else None,
        "data": dl.json_dumps(fit) if fit is not None else None,
        "t": [fit.t[i].tolist() for i in range(n_datasets)] if fit.t is not None else None,
        "V": [fit.Vexp[i].tolist() for i in range(n_datasets)] if fit.Vexp is not None else None,
        "model": [fit.model[i].tolist() for i in range(n_datasets)] if fit.model is not None else None,
        "background": [fit.bg[i].tolist() for i in range(n_datasets)] if fit.bg is not None else [None] * n_datasets,
        "P_model": [Prs[i]["sum"].tolist() for i in range(n_datasets)],
        "PUncert": [PUQs[i]["UQs"]["sum"].to_dict() for i in range(n_datasets)],
        "gof": [fit.stats[i] for i in range(n_datasets)],
    }
    return output


def run_population_fit_job(params):
    datasets = _load_datasets(params["dataset_ids"])
    fit_options = params.get("fit_options") or {}
    distance_axis = fit_options.get("distance_axis", [0, 5])
    bg_model = getattr(dl, fit_options.get("bg_model", "bg_hom3d"), dl.bg_hom3d)
    pathways = [int(p) for p in fit_options.get("pathways_options", ["1"])]
    dd_model = getattr(dl, fit_options.get("dd_model", "dd_gauss"), dl.dd_gauss)
    n_pops = fit_options.get("n_pops", 2)
    r = np.linspace(distance_axis[0], distance_axis[1], 100)
    model_params = params.get("model_params")

    n_datasets = len(datasets)
    fit = deerlab_population_fitting(datasets, model=dd_model, n_pops=n_pops, bg_model=bg_model, r=r,
                                      pathways=pathways, model_overrides=model_params, **_bootstrap_kwargs(params))
    fit.n_datasets = n_datasets
    fit.n_pops = n_pops

    fit_store = _population_fit_to_dict(fit, n_datasets)
    fit_store["populations"] = _calc_population_fractions(fit)
    fit_store["warnings"] = warnings_to_dict(check_fit_results(fit, fit.Vmodel))
    return fit_store


def _global_fit_to_dict(fit, n_datasets):
    return {
        "engine": "DeerLab",
        "fit_type": "Non-Parametric Global",
        "bg_model": fit.bg_model.name if fit.bg_model else None,
        "pathways": fit.pathways[0] if hasattr(fit, "pathways") and fit.pathways else [],
        "r": fit.r.tolist() if fit.r is not None else None,
        "model_description": fit.__str__() if fit is not None else None,
        "data": dl.json_dumps(fit) if fit is not None else None,
        "t": [fit.t[i].tolist() for i in range(n_datasets)] if fit.t is not None else None,
        "V": [fit.Vexp[i].tolist() for i in range(n_datasets)] if fit.Vexp is not None else None,
        "model": [fit.model[i].tolist() for i in range(n_datasets)] if fit.model is not None else None,
        "P_model": [fit.P[i].tolist() for i in range(n_datasets)],
        "PUncert": [fit.PUncert[i].to_dict() for i in range(n_datasets)],
        "gof": [fit.stats[i] for i in range(n_datasets)],
        "dist_stats": [dists_stats_to_list(*dl.diststats(fit.r, fit.P[i], fit.PUncert[i])) for i in range(n_datasets)],
    }


def run_global_fit_job(params):
    datasets = _load_datasets(params["dataset_ids"])
    fit_options = params.get("fit_options") or {}
    distance_axis = fit_options.get("distance_axis", [0, 5])
    bg_model = getattr(dl, fit_options.get("bg_model", "bg_hom3d"), dl.bg_hom3d)
    pathways = [int(p) for p in fit_options.get("pathways_options", ["1"])]
    r = np.linspace(distance_axis[0], distance_axis[1], 100)
    linked_params = fit_options.get("linked_params", ["pr"])
    model_overrides = params.get("model_overrides")

    n_datasets = len(datasets)
    fit = deerlab_global_fitting(datasets, linked_params, bg_model=bg_model, r=r, pathways=pathways,
                                  model_overrides=model_overrides,
                                  regparam=fit_options.get("regparam_method", "bic"),
                                  regparamrange=fit_options.get("regparamrange", [1e-8, 1e2]),
                                  **_bootstrap_kwargs(params))
    fit.n_datasets = n_datasets
    fit_store = _global_fit_to_dict(fit, n_datasets)
    fit_store["warnings"] = warnings_to_dict(check_fit_results(fit, fit.Vmodel))
    return fit_store


def run_deernet_fit_job(params):
    dataset, _mask = _load_dataset(params["dataset_id"])
    model_size = int(params["model_size"])
    deernet_folder = os.path.join(get_DeerAnalysis_directory(), "deernet", "deernet_models")

    fit = deernet2(dataset, model_size, model_dir=deernet_folder, providor=["CPUExecutionProvider"])
    dist_stats = dl.diststats(fit.r, fit.P, fit.PUncert)
    fit_dict = fit_to_dict(fit)
    fit_dict["dist_stats"] = dists_stats_to_list(*dist_stats)
    fit_dict["gof"] = fit.stats
    # DeerNet has no DeerLab model, so only the goodness-of-fit is checked
    fit_dict["warnings"] = warnings_to_dict(check_fit_results(fit, None))
    return fit_dict


JOB_HANDLERS = {
    "non-parametric_fit": run_nonparametric_fit_job,
    "parametric_fit": run_parametric_fit_job,
    "background_fit": run_background_fit_job,
    "population_fit": run_population_fit_job,
    "global_fit": run_global_fit_job,
    "deernet_fit": run_deernet_fit_job,
}


def save_fit_from_job(job, result_data):
    """Persists a completed background job's result as Fit row(s) — the same thing each
    page's manual "Save Fit" button does, but automatic, since a queued job may finish long
    after (or while) the page that queued it isn't open. Mirrors the save_fit logic that used
    to live in pages/population.py and pages/global.py for multi-dataset fits, and the
    single-row version used by the other four pages."""
    # fit_to_dict()'s PUncert/gof fields carry raw numpy arrays/scalars (e.g. from DeerLab's
    # UQResult.to_dict()), which the Fit table's JSON columns can't store directly.
    result_data = to_jsonable(result_data)

    session = get_session()
    # Prefer the name the user had in the page's fit-name input when queueing.
    fit_name = (job.params or {}).get("fit_name") or name_dataset_from_dict(result_data)

    if job.job_type in MULTI_DATASET_JOB_TYPES:
        dataset_ids = job.params.get("dataset_ids") or []
        shared = {
            "engine": result_data.get("engine"),
            "fit_type": result_data.get("fit_type"),
            "bg_model": result_data.get("bg_model"),
            "dist_model": result_data.get("dist_model"),
            "r": result_data.get("r"),
            "pathways": result_data.get("pathways"),
            "model_description": result_data.get("model_description"),
            "data": result_data.get("data"),
            # One fit across all datasets, so every row carries all of its warnings
            "warnings": result_data.get("warnings"),
        }
        gof_list = result_data.get("gof") or [None] * len(dataset_ids)
        background_list = result_data.get("background") or [None] * len(dataset_ids)
        new_fits = []
        for i, ds_id in enumerate(dataset_ids):
            new_fit = Fit(
                dataset_id=ds_id, name=fit_name,
                t=result_data["t"][i], model=result_data["model"][i],
                P_model=result_data["P_model"][i], PUncert=result_data["PUncert"][i],
                background=background_list[i], gof=gof_list[i],
                **shared,
            )
            session.add(new_fit)
            new_fits.append(new_fit)
        session.flush()
        for fit in new_fits:
            session.execute(fit_global_datasets.insert().values([
                {"fit_id": fit.id, "dataset_id": ds_id}
                for ds_id in dataset_ids if ds_id != fit.dataset_id
            ]))
            session.execute(fit_siblings.insert().values([
                {"fit_id": fit.id, "sibling_fit_id": f.id}
                for f in new_fits if f.id != fit.id
            ]))
    else:
        dataset_id = job.params.get("dataset_id")
        new_fit = Fit(dataset_id=dataset_id, name=fit_name, **result_data)
        session.add(new_fit)

    session.commit()
    session.close()

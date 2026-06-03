import deerlab as dl
import pyepr as pyepr
import xarray as xr
import inspect
import numpy as np

from deeranalysis.utils.deerlab_normal import apply_model_overrides
from deeranalysis.utils.deerlab_global import create_Vmodel

def _create_multi_pop_model_func(model, n_pops):
    # Build new param names for n_pops populations
    params = [inspect.Parameter('r', inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for i in range(n_pops):
        params.append(inspect.Parameter(f'mean{chr(ord('A') + i)}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
    for i in range(n_pops):
        params.append(inspect.Parameter(f'std{chr(ord('A') + i)}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
    for i in range(n_pops - 1):
        params.append(inspect.Parameter(f'frac{chr(ord('A') + i)}', inspect.Parameter.POSITIONAL_OR_KEYWORD))

    def func(r, *args):
        means = args[0:n_pops]
        stds  = args[n_pops:2*n_pops]
        fracs = list(args[2*n_pops:]) + [1 - sum(args[2*n_pops:])]
        Ps = [f * model(r, m, s) for m, s, f in zip(means, stds, fracs)]

        P = np.sum(Ps, axis=0)
        return P / np.trapezoid(P)

    func.__signature__ = inspect.Signature(params)
    return func

def create_multi_pop_model(model, n_pops):
    """
    Creates a DeerLab model for a mixture of n_pops populations, each described by the provided model (e.g., dl.dd_gauss).

    Attributes
    ----------
    model : function
        A DeerLab distance distribution model (e.g., dl.dd_gauss) that takes (r, mean, std) as arguments.
    n_pops : int
        The number of populations to include in the mixture model.

    Returns
    -------
    Pmodel : dl.Model
        A DeerLab model representing the mixture of n_pops populations, with parameters for means, stds, and fractions of each component.

    """
    func = _create_multi_pop_model_func(model, n_pops)
    Pmodel = dl.Model(func, constants='r')
    Pmodel.description = f"Mixture of {n_pops} {model.name} Populations"
    for i in range(n_pops):
        getattr(Pmodel, f'mean{chr(ord('A') + i)}').set(lb=1, ub=7, par0=5, description=f'Mean of Component {chr(ord('A') + i)}', unit='nm')
        getattr(Pmodel, f'std{chr(ord('A') + i)}').set(lb=0.05, ub=0.8, par0=0.1, description=f'Std of Component {chr(ord('A') + i)}', unit='nm')
    
    frac_par0 = 1 / (n_pops)
    for i in range(n_pops - 1):
        getattr(Pmodel, f'frac{chr(ord('A') + i)}').set(lb=0, ub=1, par0=frac_par0, description=f'Fraction of Component {chr(ord('A') + i)}', unit='')
    return Pmodel


# def create_Vmodel(dataset,t,r,Pmodel,pathways):

#     pathways = np.array(pathways)


#     if 'exp_type' in dataset.attrs:
#         exp_name = dataset.attrs['exp_type']
#     elif 'seq_name' in dataset.attrs:
#         exp_name = dataset.attrs['seq_name']
#     else:
#         exp_name = None
    
#     if exp_name is None:
#         Vmodel = dl.dipolarmodel(t, r, Pmodel)

#     elif exp_name == '4pDEER':
#         tau1 = dataset.attrs['tau1']/1e3
#         tau2 = dataset.attrs['tau2']/1e3
#         experiment_info= dl.ex_4pdeer(tau1, tau2,pathways=pathways[pathways<5])
#         Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
#     elif exp_name == '3pDEER':
#         tau1 = dataset.attrs['tau1']/1e3
#         experiment_info= dl.ex_3pdeer(tau1,pathways=pathways[pathways<3])
#         Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
#     elif exp_name ==  '5pDEER':
#         tau1 = dataset.attrs['tau1']/1e3
#         tau2 = dataset.attrs['tau2']/1e3
#         tau3 = dataset.attrs['tau3']/1e3
#         experiment_info= dl.ex_fwd5pdeer(tau1, tau2, tau3,pathways=pathways[pathways<9])
#         Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
#     elif exp_name == 'RIDME':
#         tau1 = dataset.attrs['tau1']/1e3
#         tau2 = dataset.attrs['tau2']/1e3
#         experiment_info= dl.ex_ridme(tau1,tau2,pathways=pathways[pathways<5])
#         Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)

#     return Vmodel

def _make_pop_model(base_model, j, i, n_pops):
    """Create a dl.Model for population j (0-indexed) in dataset i (0-indexed).

    Parameter names match the global fit: mean{X}/std{X} (shared) and
    frac{X}_{i+1} (dataset-specific). The last population's fraction is
    computed implicitly as 1 - sum(other fracs).
    """
    letter = chr(ord('A') + j)
    params = [
        inspect.Parameter('r', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter(f'mean{letter}', inspect.Parameter.POSITIONAL_OR_KEYWORD),
        inspect.Parameter(f'std{letter}', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]

    if j < n_pops - 1:
        params.append(inspect.Parameter(f'frac{letter}_{i+1}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
        def func(r, mean, std, frac):
            return frac * base_model(r, mean, std)
    else:
        for k in range(n_pops - 1):
            params.append(inspect.Parameter(f'frac{chr(ord("A") + k)}_{i+1}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
        def func(r, mean, std, *frac_others):
            return (1 - sum(frac_others)) * base_model(r, mean, std)

    func.__signature__ = inspect.Signature(params)
    return dl.Model(func, constants='r')


def _make_total_pop_model(base_model, i, n_pops):
    """Create a dl.Model for the sum of all populations in dataset i (0-indexed).

    Parameter names match the global fit: mean{X}/std{X} (shared) and
    frac{X}_{i+1} (dataset-specific). The last population's fraction is
    computed implicitly as 1 - sum(other fracs).
    """
    params = [inspect.Parameter('r', inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    for j in range(n_pops):
        params.append(inspect.Parameter(f'mean{chr(ord("A") + j)}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
    for j in range(n_pops):
        params.append(inspect.Parameter(f'std{chr(ord("A") + j)}', inspect.Parameter.POSITIONAL_OR_KEYWORD))
    for j in range(n_pops - 1):
        params.append(inspect.Parameter(f'frac{chr(ord("A") + j)}_{i+1}', inspect.Parameter.POSITIONAL_OR_KEYWORD))

    def func(r, *args):
        means = args[:n_pops]
        stds  = args[n_pops:2*n_pops]
        frac_others = list(args[2*n_pops:])
        fracs = frac_others + [1 - sum(frac_others)]
        return np.sum([f * base_model(r, m, s) for m, s, f in zip(means, stds, fracs)], axis=0)

    func.__signature__ = inspect.Signature(params)
    return dl.Model(func, constants='r')


def determine_pop_P(r, fit, P_model, n_datasets, n_pops):
    """
    Evaluate the per-population and total distance distributions from a fit result.

    For each dataset, builds a DeerLab model per population (and one for the
    total) with parameter names matching the global fit, then evaluates them
    with ``fit.evaluate`` and propagates uncertainty with ``fit.propagate``.

    Parameters
    ----------
    r : array-like
        Distance axis.
    fit : dl.FitResult
        Result returned by ``deerlab_population_fitting``.
    P_model : dl.Model
        Single-population base model (e.g. ``dl.dd_gauss``).
    n_datasets : int
        Number of datasets.
    n_pops : int
        Number of populations.

    Returns
    -------
    Prs : list of dict
        Per-dataset dicts with keys ``'A'``, ``'B'``, … and ``'sum'``,
        each containing the scaled distance distribution array.
    PUQs : list of dict
        Per-dataset dicts with the same keys, each containing a
        ``dl.UQResult`` for the corresponding distribution.
    """
    Prs = []
    PUQs = []

    for i in range(n_datasets):
        Ps  = {}
        UQs = {}

        # Per-population models
        for j in range(n_pops):
            letter = chr(ord('A') + j)
            pop_model = _make_pop_model(P_model, j, i, n_pops)
            Ps[letter]  = fit.evaluate(pop_model, r)
            UQs[letter] = fit.propagate(pop_model, r, lb=np.zeros_like(r))

        # Total (sum) model
        total_model = _make_total_pop_model(P_model, i, n_pops)
        Ps['sum']  = fit.evaluate(total_model, r)
        UQs['sum'] = fit.propagate(total_model, r, lb=np.zeros_like(r))

        # Normalise and apply scale
        scale = getattr(fit, f'scale_{i+1}')
        norm  = np.trapezoid(Ps['sum'])
        factor = scale / norm
        for key in Ps:
            Ps[key] = Ps[key] * factor

        Prs.append(Ps)
        PUQs.append({'UQs': UQs, 'factor': factor})

    return Prs, PUQs


def build_population_model_data(datasets, bg_model_name, pathways,
                                 dd_model_name, n_pops, existing_overrides=None):
    """
    Build a serialisable parameter dict for the population model edit modal.

    Constructs the full merged+linked global model so that per-dataset params
    (lam1_1, conc_2, fracA_3, …) appear alongside the shared global ones
    (meanA, stdA, …).
    """
    from deeranalysis.utils.deerlab_options import _safe_float

    r = np.linspace(1.5,6, 100)
    base_model = getattr(dl, dd_model_name, dl.dd_gauss)
    Pmodel = create_multi_pop_model(base_model, n_pops)

    Vmodels = []
    for ds in datasets:
        t = ds.coords['t'].values
        Vmodels.append(create_Vmodel(ds, t, r, Pmodel, pathways=pathways))

    global_model = dl.merge(*Vmodels)
    Nsignals = len(datasets)
    links_args = {}
    for i in range(n_pops):
        links_args[f"mean{chr(ord('A') + i)}"] = [f"mean{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]
        links_args[f"std{chr(ord('A') + i)}"] = [f"std{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]
    global_model = dl.link(global_model, **links_args)

    params_dict = {}
    for name in global_model.signature:
        if name in ('t', 'P'):
            continue
        try:
            param = getattr(global_model, name)
            if not hasattr(param, 'par0'):
                continue
            params_dict[name] = {
                'par0': _safe_float(param.par0),
                'lb': _safe_float(param.lb),
                'ub': _safe_float(param.ub),
                'frozen': bool(param.frozen),
                'description': str(param.description) if param.description else '',
                'unit': str(param.unit) if param.unit else '',
            }
        except Exception as e:
            print(f"Warning: could not serialise param {name}: {e}")

    if existing_overrides:
        for name, override in existing_overrides.items():
            if name in params_dict:
                for key in ('par0', 'lb', 'ub', 'frozen'):
                    if key in override and override[key] is not None:
                        params_dict[name][key] = override[key]

    # Detect which experiment type the first dataset is
    ds0 = datasets[0]
    attrs = ds0.attrs
    seq_name = attrs.get('seq_name', attrs.get('exp_type', '4pDEER'))

    return {
        'params': params_dict,
        'exp_type': seq_name,
        'bg_model': bg_model_name,
        'p_model': dd_model_name,
        'pathways': pathways,
    }


def background_func_population(ts, Vmodels, fit):
    """
    Compute the background for each dataset in a population fit.

    Mirrors ``background_func`` from deerlab_normal but handles the merged
    model where every parameter carries a ``_{i+1}`` suffix.

    Parameters
    ----------
    ts : list of np.ndarray
        Time axes, one per dataset.
    Vmodels : list of dl.Model
        Per-dataset dipolar models (before merging).
    fit : dl.FitResult
        Result returned by ``deerlab_population_fitting``.

    Returns
    -------
    backgrounds : list of np.ndarray
        Background trace for each dataset.
    """
    Bmodel = fit.bg_model
    backgrounds = []

    for i, (t, Vmodel) in enumerate(zip(ts, Vmodels)):
        suffix = f"_{i + 1}"
        pathways = fit.pathways[i]

        # Collect background-model parameters (skip 't' and 'lam')
        Bmodel_params = {}
        mod_depth = False
        for key in Bmodel.signature:
            if key == 'lam':
                mod_depth = True
                continue
            if key == 't':
                continue
            Bmodel_params[key] = getattr(fit, key + suffix)

        # Resolve reference times
        if hasattr(fit, f'reftime{suffix}') or hasattr(fit, f'reftime1{suffix}'):
            if len(pathways) > 1:
                reftimes = []
                for p in pathways:
                    if isinstance(p, list):
                        for j in p:
                            reftimes.append(getattr(fit, f"reftime{pathways.index(j) + 1}{suffix}"))
                    else:
                        reftimes.append(getattr(fit, f"reftime{p}{suffix}"))
            else:
                reftimes = [getattr(fit, f"reftime{suffix}")]
        elif hasattr(fit, f'tau1{suffix}'):
            expInfo = Vmodel.experimentInfo
            taus_names = expInfo.reftimes.__code__.co_varnames[:expInfo.reftimes.__code__.co_argcount]
            taus = {name: getattr(fit, name + suffix) for name in taus_names}
            reftimes = expInfo.reftimes(**taus)

        prod = 1
        scale = 1
        if len(pathways) > 1:
            for idx, p_id in enumerate(pathways):
                if isinstance(p_id, list): # Adds support for linked pathways e.g. lam23 when lam 2 =
                    lam = getattr(fit, f"lam{p_id[0]}{p_id[1]}{suffix}")
                    scale += -1 * lam
                    for j in p_id:
                        reftime = getattr(fit, f"reftime{pathways.index(j) + 1}{suffix}")
                        if mod_depth:
                            prod *= Bmodel(t=t - reftime, lam=lam, **Bmodel_params)
                        else:
                            prod *= Bmodel(t=t - reftime, **Bmodel_params)
                else:
                    reftime = reftimes[idx]
                    lam = getattr(fit, f"lam{p_id}{suffix}")
                    if mod_depth:
                        prod *= Bmodel(t=t - reftime, lam=lam, **Bmodel_params)
                    else:
                        prod *= Bmodel(t=t - reftime, **Bmodel_params)
                    scale += -1 * lam
        else:
            reftime = reftimes[0]
            lam = getattr(fit, f"mod{suffix}")
            if mod_depth:
                prod *= Bmodel(t=t - reftime, lam=lam, **Bmodel_params)
            else:
                prod *= Bmodel(t=t - reftime, **Bmodel_params)
            scale += -1 * lam

        # if hasattr(fit, f'scale{suffix}'):
        #     scale *= getattr(fit, f'scale{suffix}')

        backgrounds.append(scale * prod)

    return backgrounds


def deerlab_population_fitting(datasets, model=dl.dd_gauss, n_pops=2, bg_model=dl.bg_hom3d, verbosity=0,
                               r=None, pathways=None, model_overrides=None, **kwargs):
    """
    
    
    Parameters
    ----------
    datasets : list
        List of PyEPR datasets to fit simultaneously.

    model: str or dl.Model
        DeerLab model to use for fitting. Can be a string (e.g. 'dd_gauss') or a custom dl.Model object. Default is 'dd_gauss' (1 Gaussian distribution).

    n_pops: int
        Number of populations to fit. Default is 2.
    bg_model: str
        Background model to use. Default is 'bg_hom3d' (3D homogeneous distribution).

    verbosity: int
        Level of output during fitting. 0 for silent, 1 for basic info, 2 for detailed info. Default is 1.
    
    r: array-like
        Distance axis for the fit. If None, it will be automatically determined from the datasets.

    pathways: list of ints or list of list of ints
        List specifying which pathways to include in the fit. Can be a list of integers (e.g. [1,2]) to include the same pathways for all datasets, or a list of lists (e.g. [[1,2],[1,3]]) to specify different pathways for each dataset. If None, all pathways will be included.

    **kwargs:
        Additional keyword arguments to pass to the DeerLab fit function (e.g. regparam, fit_range, etc.).
    """

    if isinstance(datasets,xr.DataArray):
        datasets = [datasets]
    elif not isinstance(datasets,list):
        raise ValueError("Datasets should be a list of xarray DataArrays or a single DataArray.")
    
    if not isinstance(model, dl.Model) and isinstance(model, str):
        if model == 'dd_gauss':
            model = dl.dd_gauss(n_pops)
        elif model == 'dd_rice':
            model = dl.dd_rice(n_pops)
        else:
            raise ValueError(f"Unsupported model string: {model}. Supported models are 'dd_gauss' and 'dd_rice'.")
        
    elif not isinstance(model, dl.Model):
        raise ValueError("Model should be a string or a dl.Model object.")
    
    if n_pops < 1:
        raise ValueError("Number of populations (n_pops) must be at least 1.")
    elif n_pops > 5:
        raise ValueError("Number of populations (n_pops) greater than 5 may lead to unstable fits. Please consider using fewer populations or using the scripted version of DeerLab for more control.")
    
    if not isinstance(bg_model, dl.Model) and isinstance(bg_model, str):
        if hasattr(dl, bg_model):
            bg_model = getattr(dl, bg_model)
        else:
            raise ValueError(f"Unsupported background model string: {bg_model}. Please choose a valid background model from DeerLab.")
    elif not isinstance(bg_model, dl.Model):
        raise ValueError("Background model should be a string or a dl.Model object.")
    

    if pathways is None:
        pathways = [1,2,3,4,5]
    
    Vs = []
    ts = []
    for ds in datasets:
        Vexp = ds.values
        Vexp = dl.correctphase(Vexp)
        Vexp /= np.max(Vexp)
        Vs.append(Vexp)
        ts.append(ds.coords['t'].values)

    Nsignals = len(Vs)
    Vmodels = [[] for _ in range(Nsignals)]

    Pmodel = create_multi_pop_model(model, n_pops=n_pops)

    if r is None:
        r = np.linspace(1.5, 10, 100)
    
    for n,ds in enumerate(datasets):
        Vmodels[n] = create_Vmodel(ds,ds.coords['t'].values , r, Pmodel,pathways=pathways)

    global_model = dl.merge(*Vmodels)

    links_args = {}
    for i in range(n_pops):
        links_args[f"mean{chr(ord('A') + i)}"] = [f"mean{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]
        links_args[f"std{chr(ord('A') + i)}"] = [f"std{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]

    global_model = dl.link(global_model, **links_args)

    if model_overrides:
        apply_model_overrides(global_model, model_overrides)

    fit = dl.fit(global_model, Vs,**kwargs)

    fit.r = r
    fit.Pmodel = model
    fit.n_pops = n_pops
    fit.bg_model = bg_model
    # fit.datasets = datasets
    fit.Vexp = Vs
    fit.t = ts
    # fit.Vmodels = Vmodels
    fit.pathways = [pathways for i in range(Nsignals)]

    for i in range(len(fit.stats)):
        suffix = f'_{i+1}'
        p_ways = fit.pathways[i]
        if len(p_ways) == 1:
            lam_i = getattr(fit, f'mod{suffix}')
        else:
            lam_i = 0
            for p in p_ways:
                if isinstance(p, list):
                    lam_i += getattr(fit, f'lam{p[0]}{p[1]}{suffix}')
                elif hasattr(fit, f'lam{p}{suffix}'):
                    lam_i += getattr(fit, f'lam{p}{suffix}')
        fit.stats[i]['SNR'] = 1 / fit.noiselvl[i]
        fit.stats[i]['lam'] = lam_i
        fit.stats[i]['MNR'] = lam_i / fit.noiselvl[i]

    if bg_model is not None:
        fit.bg = background_func_population(ts, Vmodels, fit)
    else:
        fit.bg = None
        

    # fit.stats['SNR'] = 1/fit.noiselvl

    return fit



    
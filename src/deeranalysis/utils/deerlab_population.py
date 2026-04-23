import deerlab as dl
import pyepr as pyepr
import xarray as xr
import inspect
import numpy as np


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


def create_Vmodel(dataset,t,r,Pmodel,pathways):

    pathways = np.array(pathways)


    if 'exp_type' in dataset.attrs:
        exp_name = dataset.attrs['exp_type']
    elif 'seq_name' in dataset.attrs:
        exp_name = dataset.attrs['seq_name']
    else:
        exp_name = None
    
    if exp_name is None:
        Vmodel = dl.dipolarmodel(t, r, Pmodel)

    elif exp_name == '4pDEER':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        experiment_info= dl.ex_4pdeer(tau1, tau2,pathways=pathways[pathways<4])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
    elif exp_name == '3pDEER':
        tau1 = dataset.attrs['tau1']/1e3
        experiment_info= dl.ex_3pdeer(tau1,pathways=pathways[pathways<2])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
    elif exp_name ==  '5pDEER':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        tau3 = dataset.attrs['tau3']/1e3
        experiment_info= dl.ex_fwd5pdeer(tau1, tau2, tau3,pathways=pathways[pathways<8])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
    elif exp_name == 'RIDME':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        experiment_info= dl.ex_ridme(tau1,tau2,pathways=pathways[pathways<4])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)

    return Vmodel

def determine_pop_P(r,fit_results,P_model,n_datasets,n_pops):
    Prs = []
    for i in range(n_datasets):
        means = [fit_results[f'mean{chr(ord("A") + j)}'] for j in range(n_pops)]
        stds  = [fit_results[f'std{chr(ord("A") + j)}'] for j in range(n_pops)]
        fracs = [fit_results[f'frac{chr(ord("A") + j)}_{i+1}'] for j in range(n_pops - 1)] + [1 - sum(fit_results[f'frac{chr(ord("A") + j)}_{i+1}'] for j in range(n_pops - 1))]
        Ps = [f * P_model(r, m, s) for m, s, f in zip(means, stds, fracs)]
        Ps = {f'{chr(ord("A") + j)}': P for j, P in enumerate(Ps)}
        Ps_total = np.sum(list(Ps.values()), axis=0)
        Ps['sum'] = Ps_total
        for key in Ps:
            Ps[key] = Ps[key]/np.trapezoid(Ps_total)
        Prs.append(Ps)
    return Prs


def deerlab_population_fitting(datasets, model=dl.dd_gauss, n_pops = 2,bg_model=dl.bg_hom3d, verbosity=0,
                               r=None,pathways=None, **kwargs):
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

    fit = dl.fit(global_model, Vs,**kwargs)

    fit.r = r
    fit.Pmodel = Pmodel
    fit.bg_model = bg_model
    fit.datasets = datasets
    fit.Vexp = Vs
    fit.t = ts
    fit.pathways = pathways

    fit.stats['SNR'] = 1/fit.noiselvl

    return fit



    
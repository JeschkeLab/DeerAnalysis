

import deerlab as dl
import pyepr as pyepr
import xarray as xr
import inspect
import numpy as np
import re

def create_Vmodel(dataset,t,r,Pmodel=None,pathways=[1]):

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
        experiment_info= dl.ex_5pdeer(tau1, tau2, tau3,pathways=pathways[pathways<8])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)
    
    elif exp_name == 'RIDME':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        experiment_info= dl.ex_ridme(tau1,tau2,pathways=pathways[pathways<4])
        Vmodel = dl.dipolarmodel(t, r, Pmodel, experiment=experiment_info)

    return Vmodel

def deerlab_global_fitting(datasets,linked_params,bg_model=dl.bg_hom3d, verbosity=0,
                               r=None,pathways=None, **kwargs):
    
    """Parameters
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

    if r is None:
        r = np.linspace(1.5, 10, 100)
    
    Vmodels = [None]*len(datasets)
    
    for n,ds in enumerate(datasets):
        Vmodels[n] = create_Vmodel(ds,ds.coords['t'].values , r,pathways=pathways)

    global_model = dl.merge(*Vmodels)

    # Link parameters across models
    links_args = {}
    if 'pr' in linked_params:    
        links_args[f"P"] = [f"P_{j+1}" for j in range(len(datasets))]

    if 'background' in linked_params:
        links_args[f"conc"] = [f"conc_{j+1}" for j in range(len(datasets))]

    if 'mod-depth' in linked_params:
        if 'mod' in global_model.signature:
            links_args[f"mod"] = [f"mod_{j+1}" for j in range(len(datasets))]
        else:
            parameters = global_model.signature

            pathway_numbers = [re.findall(r'lam(\d+)', param) for param in parameters]
            unique_pathway_numbers = set([num for sublist in pathway_numbers for num in sublist])

            for pathway in unique_pathway_numbers:
                lam_params = [
                    f'lam{pathway}_{j+1}'
                    for j in range(Nsignals)
                    if f'lam{pathway}_{j+1}' in parameters
                ]
                if len(lam_params) > 0:
                    links_args[f'lam{pathway}'] = lam_params

    global_model = dl.link(global_model, **links_args)


    fit = dl.fit(global_model, Vs,**kwargs)

    fit.r = r
    fit.bg_model = bg_model
    fit.datasets = datasets
    fit.Vexp = Vs
    fit.t = ts
    fit.pathways = pathways

    fit.stats['SNR'] = 1/fit.noiselvl

    return fit

def extract_global_P(fit):
    if hasattr(fit, 'P'):
        return fit.P
    else:
        P_keys = [key for key in fit.params if key.startswith('P')]
        return [fit.params[key] for key in P_keys]
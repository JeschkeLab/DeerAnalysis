

import deerlab as dl
import pyepr as pyepr
import xarray as xr
import inspect
import numpy as np
import re

from deeranalysis.utils.deerlab_normal import apply_model_overrides

def create_Vmodel(dataset,t,r,Pmodel=None,Bmodel=dl.bg_hom3d, pathways=[1]):

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
        experiment_info= dl.ex_4pdeer(tau1, tau2,pathways=pathways[pathways<5])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    
    elif exp_name == '3pDEER':
        tau1 = dataset.attrs['tau1']/1e3
        experiment_info= dl.ex_3pdeer(tau1,pathways=pathways[pathways<3])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    elif exp_name == 'single':
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel)
    
    elif exp_name ==  '5pDEER':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        tau3 = dataset.attrs['tau3']/1e3
        experiment_info= dl.ex_5pdeer(tau1, tau2, tau3,pathways=pathways[pathways<9])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    
    elif exp_name == 'RIDME':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        experiment_info= dl.ex_ridme(tau1,tau2,pathways=pathways[pathways<5])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    
    elif exp_name == 'SIFTER':
        tau1 = dataset.attrs['tau1']/1e3
        tau2 = dataset.attrs['tau2']/1e3
        experiment_info= dl.ex_sifter(tau1,tau2,pathways=pathways[pathways<5])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    elif exp_name == 'DQC':
        tau1 = dataset.attrs['tau1']/1e3
        experiment_info= dl.ex_dqc(tau1,pathways=pathways[pathways<3])
        Vmodel = dl.dipolarmodel(t, r, Pmodel,Bmodel=Bmodel, experiment=experiment_info)
    else:
        raise ValueError(f"Unsupported experiment type: {exp_name}. Supported types are '4pDEER', '3pDEER', '5pDEER', 'RIDME', 'SIFTER', and 'DQC'. Please ensure the dataset has the correct 'exp_type' attribute.")

    return Vmodel

def build_global_model_data(datasets,*, bgmodel,linked_params,pathways,existing_overrides=None):
    from deeranalysis.utils.deerlab_options import _safe_float
    r = np.linspace(1.5,6, 100)
    Nsignals = len(datasets)
    Vmodels = [None]*Nsignals
    
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
        if 'mod_1' in global_model.signature:
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

                            
    return {
        'params': params_dict,
        'exp_type': None,
        'bg_model': None,
        'p_model': None,
        'pathways': pathways,
    }

def deerlab_global_fitting(datasets,linked_params,bg_model=dl.bg_hom3d, verbosity=0,
                               r=None,pathways=None,model_overrides=None, **kwargs):
    
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
        if 'mod_1' in global_model.signature:
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
    if model_overrides:
        apply_model_overrides(global_model, model_overrides)


    fit = dl.fit(global_model, Vs,**kwargs)

    fit.r = r
    fit.bg_model = bg_model
    fit.Vexp = Vs
    fit.t = ts
    fit.pathways =  [pathways for i in range(Nsignals)]
    fit.background = background_func_global(ts,Vmodels,fit)
    fit.P, fit.PUncert = extract_global_P(fit)

    if 'mod-depth' in linked_params:
        # Calculate the total modulation depth for each dataset by summing the contributions from all pathways
        if 'mod' in global_model.signature:
            lam = getattr(fit, 'mod')
        else:
            # sum all lam parameters that match the pattern 'lam{pathway}'
            lam = 0
            for key in global_model.signature:
                if re.match(r'lam\d+', key):
                    lam += getattr(fit, key)
    else:
        lam = []
        for i in range(Nsignals):
            p_ways = fit.pathways[i]
            if len(p_ways) == 1:
                lam.append(getattr(fit, f'mod_{i+1}'))
            elif len(p_ways) > 1:
                lam_i = 0
                for p in p_ways:
                    if f'lam{p}' in global_model.signature:
                        lam_i += getattr(fit, f'lam{p}')
                    elif f'lam{p}_{i+1}' in global_model.signature:
                        lam_i += getattr(fit, f'lam{p}_{i+1}')
                lam.append(lam_i)
                
    for i in range(len(fit.stats)):
        fit.stats[i]['SNR'] = 1/fit.noiselvl[i]
        fit.stats[i]['lam'] = lam if isinstance(lam, (int, float)) else lam[i]
        fit.stats[i]['MNR'] = fit.stats[i]['lam'] / fit.noiselvl[i]
    # fit.stats['SNR'] = 1/fit.noiselvl

    return fit

def extract_global_P(fit):
    n_datasets = len(fit.Vexp)
    if hasattr(fit, 'P'):
        Ps = [fit.P for i in range(n_datasets)]
        Puncerts = [fit.PUncert for i in range(n_datasets)]
        return Ps, Puncerts
    else:

        return [getattr(fit, f'P_{i+1}') for i in range(n_datasets)], [getattr(fit, f'P_{i+1}Uncert') for i in range(n_datasets)]
    
    
def background_func_global(ts,Vmodels,fit):
    """ 
    Computes the background function for each dataset. 

    Currently limited to normal paramterization. 
    

    Parameters
    ----------
    ts: list of arrays
        List of time axes for each dataset.
    Vmodels: list of dl.Models
        List of DeerLab models for each dataset, prior to merging.
    fit: dl.Fit
        The result of the global fit, containing the fitted parameters and the background model.
    Return:
    ------
    bg_funcs: list of arrays
        List of background functions for each dataset, evaluated at the time points of the datasets.

    """
    
    Bmodel = fit.bg_model
    physical_model = 'lam' in Bmodel.signature
    backgrounds = []

    for i, (t, Vmodel) in enumerate(zip(ts, Vmodels)):
        suffix = f"_{i+1}"
        pathways = fit.pathways[i]

        Bmodel_params = {}

        for key in Bmodel.signature:
            if key in ['lam', 't']:
                continue # These parameters are handled separately below
            elif hasattr(fit, key): # The parameter is globalised so it has no suffix
                Bmodel_params[key] = getattr(fit, key)
            elif hasattr(fit, f"{key}{suffix}"): # The parameter is not globalised so we look for the suffixed version
                Bmodel_params[key] = getattr(fit, f"{key}{suffix}")
        prod = 1
        scale = 1

        if len(pathways) > 1:
            for idx, p_id in enumerate(pathways):
                if isinstance(p_id, list): # Adds support for linked pathways e.g. lam23 when lam 2 = lam3
                    if hasattr(fit,f"lam{p_id[0]}{p_id[1]}"):# The modulation depth is globalised so it has no suffix
                        lam = getattr(fit, f"lam{p_id[0]}{p_id[1]}")
                    else:
                        lam = getattr(fit, f"lam{p_id[0]}{p_id[1]}{suffix}")
                    scale += -1 * lam
                    for j in p_id:
                        reftime = getattr(fit, f"reftime{p_id}{suffix}")
                        if physical_model:
                            prod *= Bmodel(t=t - reftime, lam=lam, **Bmodel_params)
                        else:
                            prod *= Bmodel(t=t - reftime, **Bmodel_params)
                else:
                    reftime = getattr(fit, f"reftime{p_id}{suffix}")
                    if hasattr(fit, f"lam{p_id}"): # The modulation depth is globalised so it has no suffix
                        lam = getattr(fit, f"lam{p_id}")
                    else:
                        lam = getattr(fit, f"lam{p_id}{suffix}")
                    if physical_model:
                        prod *= Bmodel(t=t - reftime, lam=lam, **Bmodel_params)
                    else:
                        prod *= Bmodel(t=t - reftime, **Bmodel_params)
                    scale += -1 * lam
        else:
            reftime = getattr(fit, f"reftime{suffix}")
            if hasattr(fit, 'mod'): # If the modulation depth is globalised, it has no suffix
                lam = getattr(fit, f"mod")
            else:
                lam = getattr(fit, f"mod{suffix}")
            if physical_model:
                prod *= Bmodel(t=t-reftime, lam = lam,**Bmodel_params)
            else:
                prod *= Bmodel(t=t-reftime, **Bmodel_params)
            scale += -1 * lam
        backgrounds.append(scale * prod)

    return backgrounds
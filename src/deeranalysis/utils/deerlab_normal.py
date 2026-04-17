import numpy as np
from scipy.optimize import curve_fit
import deerlab as dl
import matplotlib.pyplot as plt
from scipy.integrate import cumulative_trapezoid
import logging
import importlib
import scipy.fft as fft
from deerlab import correctphase
from scipy.interpolate import interp1d
import re
import numbers
import scipy.signal as sig
from scipy.optimize import minimize,brute
import scipy.optimize as opt
import scipy.signal as signal


def MNR_estimate(Vexp, t, mask=None, norm=False):
    """
    Estimates the Modulation to Noise Ratio (MNR) of a DEER signal without fitting.
    This is done by applying a low pass filter to remove noise and then finding the peaks in the signal.

    Parameters
    ----------
    Vexp : np.ndarray
        The experimental DEER signal, real part only.
    t : np.ndarray
        The time axis of the DEER signal, in microseconds.
    mask : np.ndarray, optional
        The mask to apply to the data, by default None
    norm : bool, optional
        If True, the MNR will be normalised for sampling density, by default False
    
    Returns
    -------
    float
        The estimated MNR of the dataset.
    """
    if mask is not None:
        Vexp = Vexp[mask]
        t = t[mask]
    Vexp/=Vexp.max()

    
    # Vexp /= Vexp.max()
    SNR = 1/dl.noiselevel(Vexp)
    # Smoothing spline with a low-pass filter
    b,a = signal.butter(3,0.1) # 3rd order Butterworth low-pass filter with cutoff at 0.1 MHz
    Vexp_smooth = signal.filtfilt(b,a,Vexp)
    min_point = np.min(Vexp_smooth)
    N_points = len(Vexp_smooth)
    peaks = signal.find_peaks(
        Vexp_smooth, height=min_point,distance=N_points//4)
    
    est_lam = np.sum(peaks[1]['peak_heights']-min_point)
    MNR = est_lam*SNR
    return MNR

def val_in_us(Param):
    if len(Param.axis) == 0:
        if Param.unit == "us":
            return Param.value
        elif Param.unit == "ns":
            return Param.value / 1e3
    elif len(Param.axis) == 1:
        if Param.unit == "us":
            return Param.value + Param.axis[0]['axis']
        elif Param.unit == "ns":
            return (Param.value + Param.axis[0]['axis']) / 1e3 



def deerlab_fitting(dataset, compactness=True, model=None, exp_type='5pDEER', verbosity=0,
                 remove_crossing=True, bg_model=dl.bg_hom3d, **kwargs):
    """
    Analyze DEER data using DeerLab.
    This function performs a full analysis of a DEER dataset, including background correction,
    modulation depth estimation, and distance distribution fitting.
    Parameters
    ----------
    dataset : object
        A dataset object containing DEER experiment data, either as a complex signal,
        or a preprocessed real signal.
    compactness : bool, optional
        Whether to apply a compactness penalty during the fit (default: True).
        Only used when model=None (model-free analysis).
    model : callable, optional
        Model for the distance distribution P(r). If None, a model-free analysis is performed
        (default: None).
    ROI : bool, optional
        Whether to identify and return the region of interest (default: False).
    exp_type : str, optional
        Type of DEER experiment ('3pDEER', '4pDEER', or '5pDEER') (default: '5pDEER').
    verbosity : int, optional
        Level of verbosity for output information (default: 0).
    remove_crossing : bool, optional
        Whether to remove crossing echoes from the data. Only works with complex data 
        (default: True).
    bg_model : callable, optional
        Background model to use (default: dl.bg_hom3d).
    **kwargs : dict, optional
        Additional keyword arguments:
        - tau1, tau2, tau3 : float
            Tau values for the experiment in microseconds.
        - mask : array_like
            Mask for the experimental data.
        - pathways : list
            List of pathway contributions to include.
        - pulselength : float
            Length of the pulse in nanoseconds.
        - r : array_like
            Distance axis for the distribution.
        - regparam : str
            Method for regularization parameter selection ('bic' by default).
        - nnlsSolver : str
            Non-negative least squares solver ('qp' by default).
        - parametrization : str
            Method to parametrize the model ('reftimes' by default).
        - Vmodel : object
            Pre-constructed dipolar model.
        - bounds : dict
            Dictionary with bounds for model parameters.
    Returns
    -------
    fit : object
        Fit result object containing the fitted parameters, distance distribution,
        and other analysis results.
    rec_tau_max : float, optional
        Recommended maximum tau value. Only returned if ROI=True.
    Notes
    -----
    The function automatically extracts parameters from the dataset if available,
    otherwise it relies on the parameters passed via kwargs.
    """
                 
    Vexp:np.ndarray = dataset.data 

    if np.iscomplexobj(Vexp):
        Vexp,Vexp_im,_ = dl.correctphase(Vexp,full_output=True)
    elif remove_crossing:
        Warning("Crossing removal only works with complex data. Skipping")
        remove_crossing = False

    Vexp /= Vexp.max()

    # Extract params from dataset

    if hasattr(dataset,"sequence"):
        sequence = dataset.sequence
        if sequence.name == "4pDEER":
            exp_type = "4pDEER"
            tau1 = val_in_us(sequence.tau1)
            tau2 = val_in_us(sequence.tau2)

        elif sequence.name == "5pDEER":
            exp_type = "5pDEER"
            tau1 = val_in_us(sequence.tau1)
            tau2 = val_in_us(sequence.tau2)
            tau3 = val_in_us(sequence.tau3)

        elif sequence.name == "3pDEER":
            exp_type = "3pDEER"
            tau1 = val_in_us(sequence.tau1)

        elif sequence.name == "nDEER-CP":
            exp_type = "4pDEER"
            tau1 = val_in_us(sequence.tau1)
            tau2 = val_in_us(sequence.tau2)

        tp = find_longest_pulse(sequence)
        t = val_in_us(sequence.t)
    
    elif 't' in dataset.coords: # If the dataset is a xarray and has sequence data
        t = dataset['t'].data
        if 'seq_name' in dataset.attrs:
            if dataset.attrs['seq_name'] == "4pDEER":
                exp_type = "4pDEER"
                tau1 = dataset.attrs['tau1'] / 1e3
                tau2 = dataset.attrs['tau2'] / 1e3
            elif dataset.attrs['seq_name'] == "5pDEER":
                exp_type = "5pDEER"
                tau1 = dataset.attrs['tau1'] / 1e3
                tau2 = dataset.attrs['tau2'] / 1e3
                tau3 = dataset.attrs['tau3'] / 1e3
            elif dataset.attrs['seq_name'] == "3pDEER":
                exp_type = "3pDEER"
                tau1 = dataset.attrs['tau1'] / 1e3
        else:
            if 'tau1' in dataset.attrs:
                tau1 = dataset.attrs['tau1'] / 1e3
            elif 'tau1' in kwargs:
                tau1 = kwargs.pop('tau1')
            else:
                raise ValueError("tau1 not found in dataset or kwargs")
            if 'tau2' in dataset.attrs:
                tau2 = dataset.attrs['tau2'] / 1e3
            elif 'tau2' in kwargs:
                tau2 = kwargs.pop('tau2')
            else:
                raise ValueError("tau2 not found in dataset or kwargs")
            if 'tau3' in dataset.attrs:
                tau3 = dataset.attrs['tau3'] / 1e3
                exp_type = "5pDEER"
            elif 'tau3' in kwargs:
                tau3 = kwargs.pop('tau3')
                exp_type = "5pDEER"
            else:
                exp_type = "4pDEER"

    else:
        # Extract params from kwargs
        if "tau1" in kwargs:
            tau1 = kwargs.pop("tau1")
        if "tau2" in kwargs:
            tau2 = kwargs.pop("tau2")
        if "tau3" in kwargs:
            tau3 = kwargs.pop("tau3")
        exp_type = kwargs.pop("exp_type")
        # t = dataset.axes[0]
        t = dataset['X']

    if t.max() > 500:
        t /= 1e3

    # Find mask if needed

    if remove_crossing:
        mask = None
        if 'pcyc_name' in dataset.attrs:
            pcyc = dataset.attrs['pcyc_name']
        elif 'nPcyc' in dataset.attrs: # guess pcyc
            if dataset.attrs['nPcyc'] == 16:
                pcyc = 'Full'
            elif dataset.attrs['nPcyc'] == 8:
                pcyc = '8-step'
            elif dataset.attrs['nPcyc'] == 2:
                pcyc = 'DC'
            else:
                pcyc = f'{dataset.attrs["nPcyc"]}-step'
        else:
            pcyc = 'unknown'

        if pcyc == 'DC' and exp_type == "5pDEER": # Remove crossing echoes
            t_position = [tau1 + tau2 - tau3]
            idx_position = [np.argmin(np.abs(cross - t)) for cross in t_position]
            mask = np.ones_like(Vexp, bool)
            for loc in idx_position:
                mask &= remove_echo(Vexp, Vexp_im, loc, criteria=4, extent=3)

    if "mask" in kwargs:
        mask = kwargs["mask"]
        noiselvl = dl.noiselevel(Vexp[mask])
    elif remove_crossing and mask is not None:
        noiselvl = dl.noiselevel(Vexp[mask])
    else:
        noiselvl = dl.noiselevel(Vexp)
        mask=None

    # Determine the pathways
    est_MNR = MNR_estimate(Vexp,t,mask=mask)

    if "pathways" in kwargs:
        pathways = kwargs.pop("pathways")
    else: 
        if exp_type == '4pDEER':
            if est_MNR < 40:
                pathways = [1]
            else:
                pathways = [1,2,3,4]
        elif exp_type == '5pDEER':
            if est_MNR < 40:
                pathways = [1,5]
            else:
                pathways = [1,2,3,4,5]

        elif exp_type == '3pDEER':
            pathways = [1,2]
        else:
            pathways = None

    if model is not None: # Compactness is only needed with model-free fitting
        compactness = False
    

    if verbosity > 1:
        print(f"Experiment type: {exp_type}, pathways: {pathways}")
        print(f"Experimental Parameters set to: tau1 {tau1:.2f} us \t tau2 {tau2:.2f} us")

    if "pulselength" in kwargs:
        pulselength = kwargs.pop("pulselength")/1e3
    elif hasattr(dataset,"sequence"):
        pulselength = tp/4
    elif hasattr(dataset,'attrs') and "pulse0_tp" in dataset.attrs:
        # seach over all pulses to find the longest pulse using regex
        pulselength = np.max([dataset.attrs[i] for i in dataset.attrs if re.match(r"pulse\d*_tp", i)])
        pulselength /= 1e3 # Convert to us
        pulselength /= 4 # The automated procedure does not require such broad allowances
    else:
        pulselength = 16/1e3
        
    if exp_type == "4pDEER":
        experimentInfo = dl.ex_4pdeer(tau1=tau1,tau2=tau2,pathways=pathways,pulselength=pulselength)
    elif exp_type == "5pDEER":
        experimentInfo = dl.ex_fwd5pdeer(tau1=tau1,tau2=tau2,tau3=tau3,pathways=pathways,pulselength=pulselength)
    elif exp_type == "3pDEER":
        experimentInfo = dl.ex_3pdeer(tau=tau1,pathways=pathways,pulselength=pulselength)

    if 'r' in kwargs:
        r = kwargs.pop('r')
        r_max = r.max()
    else:
        r_max = np.ceil(np.cbrt(t.max()*6**3/2))
        if r_max > 11.5:
            nPoints = 300
        else:
            nPoints = 150
        r = np.linspace(1.5,r_max,nPoints)

    # Default fit parameters
    defualt_fit_params = {'regparam':'bic','nnlsSolver':'qp'}
    for key in defualt_fit_params:
        if key not in kwargs:
            kwargs[key] = defualt_fit_params[key]

    # identify experiment
    if 'parametrization' in kwargs:
        parametrization = kwargs.pop('parametrization')
    else:
        parametrization = 'reftimes'

    
    if 'Vmodel' in kwargs:
        Vmodel = kwargs['Vmodel']
    else:
        Vmodel = dl.dipolarmodel(t, r, experiment=experimentInfo, Pmodel=model,Bmodel=bg_model,parametrization=parametrization)
        Vmodel.pathways = pathways
        Vmodel.experimentInfo = experimentInfo
        Vmodel.pulselength = pulselength

    if 'bounds' in kwargs:
        bounds = kwargs.pop('bounds')
        for key in bounds:
            if hasattr(Vmodel, key):
                getattr(Vmodel, key).set(lb=bounds[key][0], ub=bounds[key][1])

    if 'model_overrides' in kwargs:
        overrides = kwargs.pop('model_overrides')
        if overrides:
            for param_name, param_data in overrides.items():
                if not hasattr(Vmodel, param_name):
                    continue
                param = getattr(Vmodel, param_name)
                if not hasattr(param, 'set'):
                    continue
                lb = param_data.get('lb')
                ub = param_data.get('ub')
                par0 = param_data.get('par0')
                frozen = param_data.get('frozen', False)
                if lb is not None and ub is not None:
                    param.set(lb=lb, ub=ub)
                elif lb is not None:
                    param.set(lb=lb)
                elif ub is not None:
                    param.set(ub=ub)
                if par0 is not None:
                    param.set(par0=par0)
                if frozen:
                    param.freeze(par0 if par0 is not None else param.par0)
                else:
                    param.unfreeze()
            

    if compactness:
        compactness_penalty = dl.dipolarpenalty(model, r, 'compactness', 'icc')
        compactness_penalty.weight.set(lb=5e-3, ub=2e-1)
        # compactness_penalty.weight.freeze(0.04)

    else:
        compactness_penalty = None



    # Cleanup extra args
    extra_args = ['tau1','tau2','tau3','exp_type','model','bg_model','compactness','ROI','verbosity','pulselength','Vmodel','parametrization']
    for arg in extra_args:
        if arg in kwargs:
            kwargs.pop(arg)

    # Core 
    if verbosity > 1:
        print('Starting Fitting')
    fit = dl.fit(Vmodel, Vexp, penalties=compactness_penalty, 
                 noiselvl=noiselvl,
                 verbose=verbosity,
                 **kwargs)
    if verbosity > 1:
        print('Fit complete')
    mod_labels = re.findall(r"(lam\d*)'", str(fit.keys()))
    if mod_labels == []:
        mod_labels= ['mod']

    lam = 0
    for mod in mod_labels:
        lam += getattr(fit, mod)

    MNR = lam/fit.noiselvl
    fit.MNR = MNR
    fit.lam = lam


    fit.Vmodel = Vmodel
    fit.Bmodel = bg_model
    fit.Pmodel = model
    fit.dataset = dataset
    fit.r = r
    fit.Vexp = Vexp
    fit.t = t
    fit.mask = mask

    fit.background = background_func(t, fit)
    fit.stats['MNR'] = MNR
    fit.stats['SNR'] = 1/fit.noiselvl

    if not hasattr(fit, "P"):
        fit.P = fit.evaluate(model,r)
        fit.PUncert = fit.propagate(model,r, lb=np.zeros_like(r))
    
    
    return fit

def background_func(t, fit):
    Vmodel = fit.Vmodel
    Bmodel = fit.Bmodel
    pathways = Vmodel.pathways
    
    # Extract the parameters from the background model
    Bmodel_params = {}
    mod_depth=False
    for key in Bmodel.signature:
        if key == 'lam':
            mod_depth=True
            continue
        if key == 't':
            continue
        Bmodel_params[key] = getattr(fit, key)

    # get all reftimes
    if hasattr(fit, 'reftime') or hasattr(fit, 'reftime1'):
        if len(pathways) > 1:
            reftimes = []
            for i in pathways:
                if isinstance(i, list):
                    # linked pathway
                    for j in i:
                        reftimes.append(getattr(fit, f"reftime{pathways.index(j)+1}"))
                else:
                    reftimes.append(getattr(fit, f"reftime{i}"))
        else:
            reftimes = [getattr(fit, "reftime")]
    elif hasattr(fit, 'tau1'):
        expInfo = Vmodel.experimentInfo
        taus_names = expInfo.reftimes.__code__.co_varnames[:expInfo.reftimes.__code__.co_argcount]
        taus = {i:getattr(fit, i) for i in taus_names}
        reftimes = expInfo.reftimes(**taus)

    prod = 1
    scale = 1
    if len(pathways) > 1:
        for i,p_id in enumerate(pathways):
            if isinstance(p_id, list):
                # linked pathway
                lam = getattr(fit, f"lam{p_id[0]}{p_id[1]}")
                scale += -1 * lam
                for j in i:
                    reftime = getattr(fit, f"reftime{pathways.index(j)+1}")
                    if mod_depth:
                        prod *= Bmodel(t=t-reftime,lam=lam,**Bmodel_params)
                    else:
                        prod *= Bmodel(t=t-reftime, **Bmodel_params)

            else:
                reftime = reftimes[i]
                # reftime = getattr(fit, f"reftime{i}")
                lam = getattr(fit, f"lam{p_id}")
                if mod_depth:
                    prod *= Bmodel(t=t-reftime,lam=lam,**Bmodel_params)
                else:
                    prod *= Bmodel(t=t-reftime, **Bmodel_params)

                scale += -1 * lam
    else:
        # reftime = getattr(fit, f"reftime")
        reftime = reftimes[0]
        lam = getattr(fit, f"mod")
        if mod_depth:
            prod *= Bmodel(t=t-reftime,lam=lam,**Bmodel_params)
        else:
            prod *= Bmodel(t=t-reftime, **Bmodel_params)
        scale += -1 * lam
    
    if hasattr(fit,'P_scale'):
        scale *= fit.P_scale
    elif hasattr(fit,'scale'):
        scale *= fit.scale

    return scale * prod

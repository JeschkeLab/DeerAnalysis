import deerlab as dl
import plotly.graph_objs as go
import numpy as np
import xarray as xr

regparam_options = [
    {"label": "Akaike information criterion (AIC)", "value": "aic"},
    {"label": "Bayesian information criterion (BIC)", "value": "bic"},
    {"label": "Generalized cross-validation (GCV)", "value": "gcv"},
    {"label": "L-curve minimum-radius method (LR)", "value": "lr"},
    {"label": "L-curve maximum curvature method (LC)", "value": "lc"},
    {"label": "Empirical Bayesian method (EB)", "value": "eb"}
]

experiment_type_options = [
    {"label": "4-pulse DEER", "value": "4pDEER", "max_pathways": 4},
    {"label": "3-pulse DEER", "value": "3pDEER", "max_pathways": 3},
    {"label": "5-pulse DEER", "value": "5pDEER", "max_pathways": 5},
    {"label": "RIDME", "value": "RIDME"},
    {"label": "SIFTER", "value": "SIFTER"}
    ]

background_models = [
    {'label': 'None', 'value': 'none'},
    {'label': 'Homogeneous 3D', 'value': 'bg_hom3d'},
    {'label': 'Exponential', 'value': 'bg_exp'}
]

parametric_models = [
        {'label': '1 Gaussian', 'value': 'dd_gauss'},
        {'label': '2 Gaussians', 'value': 'dd_gauss2'},
        {'label': '3 Gaussians', 'value': 'dd_gauss3'},
        {'label': '1 3D Rice', 'value': 'dd_rice'},
        {'label': '2 3D Rice', 'value': 'dd_rice2'},
        {'label': '3 3D Rice', 'value': 'dd_rice3'},
        {'label': 'Generalized Gaussian', 'value': 'dd_gengauss'},
        {'label': 'Skew Gaussian', 'value': 'dd_skewgauss'},
        {'label': 'Worm Chain', 'value': 'dd_wormchain'},
        {'label': 'Gaussian Worm Chain', 'value': 'dd_wormcgauss'},
        {'label': 'Random Coil', 'value': 'dd_randcoil'}
]
colour_scheme_dark = ['#7C37DB','#DB7C17','#166122']
colour_scheme_light = ['#A787D6',"#EDA659",'#67B875']

def plotly_goodness_of_fit(results=None):
    """
    Returns a plotly version of the goodness of fit plot for a DeerLab fit result object `dl.plot(gof=True)`.

    Three Plots:
    1. Plot of residuals. along with the estimated noise level (±2σ) as dashed lines and mean value as a dotted line.
    2. Histogram of residuals with an overlaid normal distribution fit.
    3. Auto-correlation of residuals with confidence intervals for white noise.
    """

    # Make a 3-column subplot in plotly
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=3, subplot_titles=["Residuals", "Residuals Histogram", "Residuals Autocorrelation"],
                        horizontal_spacing=0.01)
    
    if results is None:
        # If no results provided, return empty plots with titles
        return fig

    data_color = "#3409b6"  # Default plotly blue
    grey_color = "#ACACAC"  # Grey for confidence intervals

    # Plot 1: Residuals with noise level and mean
    fig.add_trace(go.Scatter(x=results.dataset.t, y=results.residuals, mode='markers', name='Residuals', line={'color':data_color}), row=1, col=1)
    fig.add_trace(go.Scatter(x=results.dataset.t, y=2*results.noiselvl*np.ones_like(results.dataset.t), mode='lines', name='2σ', line=dict(dash='dash',color=grey_color),showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=results.dataset.t, y=-2*results.noiselvl*np.ones_like(results.dataset.t),fill='tonexty', mode='lines', name='±2σ', line=dict(color=grey_color)), row=1, col=1)
    # fig.add_trace(go.Scatter(x=results.dataset.t, y=np.mean(results.residuals)*np.ones_like(results.dataset.t), mode='lines', name='Mean', line=dict(dash='dot')), row=1, col=1)


    # Plot 2: Histogram of residuals with normal distribution fit
    norm_residuals = (results.residuals - np.mean(results.residuals)) / np.std(results.residuals)
    hist_data = np.histogram(norm_residuals, bins=20,range=(-4,4), density=True)
    x_hist = (hist_data[1][:-1] + hist_data[1][1:]) / 2  # Bin centers
    x = np.linspace(-4, 4, 100)
    y_hist = hist_data[0]
    fig.add_trace(go.Bar(x=x_hist, y=y_hist, name='Residuals',marker={'color':data_color}), row=1, col=2)
    fig.add_trace(go.Scatter(x=x, y=(1/np.sqrt(2*np.pi))*np.exp(-0.5*x**2), mode='lines', name='Normal Fit', showlegend=True), row=1, col=2)
    fig.update_yaxes(visible=False, row=1, col=2)

    fig.update_xaxes(range=[-4, 4], row=1, col=2)


    # Plot 3: Autocorrelation of residuals with confidence intervals
    maxLag = len(norm_residuals)-1
    acorr = np.correlate(results.residuals, results.residuals, mode='full')
    #normed
    acorr = acorr / np.dot(results.residuals, results.residuals)
    lags = np.arange(-len(results.residuals)+1, len(results.residuals))
    acorr = acorr[lags>-0.5]
    lags = lags[lags>-0.5]
    conf_interval = 1.96 / np.sqrt(len(results.residuals))  # 95% confidence interval for white noise
    fig.add_trace(go.Scatter(x=lags, y=acorr, mode='lines', name='Residuals', line={'color':data_color}), row=1, col=3)
    threshold = 1.96/np.sqrt(len(results.residuals))
    fig.add_trace(go.Scatter(x=lags, y=threshold*np.ones_like(lags), fill=None, mode='lines', line=dict(color=grey_color),showlegend=False), row=1, col=3)
    fig.add_trace(go.Scatter(x=lags, y=-threshold*np.ones_like(lags), fill='tonexty', mode='lines', name='White Noise Confidence Region', line=dict(color=grey_color)), row=1, col=3,)

    # Set lower x lim
    fig.update_xaxes(range=[-0.5, maxLag], row=1, col=3)
    fig.update_yaxes(visible=False, row=1, col=3)


    return fig


def plotly_comparison(results,titles=None):
    """
    Compares mutliple fits or datasets by plotting thier time domain data and distance distributions in a single plotly figure with two subplots.

    The input is not xr.dataarray or dl.FitResult but rather a list of dicts with the following structure:
    {
    "name": "Fit 1",
    "t": [time axis],
    "model": [fitted model],
    "P": [distance distribution],
    "PUncert": [distance distribution uncertainty]
    }

    Parameters
    ----------
    *fits : list of dicts 
    
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Time Domain", "Distance Distribution"], horizontal_spacing=0.1)
    
    # If no fits provided, return empty figure with titles
    if results is None or len(results) == 0:
        return fig
    
    if titles is None:
        titles = [f"Fit {i+1}" for i in range(len(results))]

    colour_scheme_dark = ['#7C37DB','#DB7C17','#166122']
    colour_scheme_light = ['#A787D6',"#EDA659",'#67B875']

    # Set axes labels
    fig.update_xaxes(title_text="Time (µs)", row=1, col=1)
    fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
    fig.update_xaxes(title_text="Distance (nm)", row=1, col=2)
    fig.update_yaxes(title_text="P(r) (nm⁻¹)", row=1, col=2)

    vspacing = np.linspace(0, 0.5, len(results))

    for i, res in enumerate(results):
        if isinstance(res, dl.FitResult):

            data_t = res.dataset.t.values
            data_V = res.Vexp + vspacing[i]  # Shift data up by vspacing[i] for better visibility
            data_model = res.model + vspacing[i]  # Shift model up by vspacing[i] for better visibility
            PUncert = res.PUncert.ci(95) 
            r = res.r
            P = res.P
        elif isinstance(res, dict):
            data_t = res['t']
            data_V = res['V'] + vspacing[i]  # Shift data up by vspacing[i] for better visibility
            data_model = res['model'] + vspacing[i]  # Shift model up by vspacing[i] for better visibility
            r = res['r']
            P = res['P']
            PUncert = res['PUncert'] if 'PUncert' in res else None
        else:
            raise ValueError("Each fit result must be either a dl.FitResult, xr.DataArray or a dict. Invalid type: {}".format(type(res)))
        fig.add_trace(go.Scatter(
            x=data_t, y=data_V, mode='markers', name='Data',
            legendgroup=titles[i],legendgrouptitle_text=titles[i],
            line={'color':colour_scheme_light[i]}), row=1, col=1)
        fig.add_trace(go.Scatter(x=data_t, y=data_model, mode='lines', name='Model', legendgroup=titles[i], line={'color':colour_scheme_dark[i]}), row=1, col=1)

        fig.add_trace(go.Scatter(x=r, y=P, mode='lines', name='P(r)', legendgroup=titles[i], line={'color':colour_scheme_dark[i]}), row=1, col=2)
        if PUncert is not None:
            fig.add_trace(go.Scatter(x=r, y=PUncert[:,0], mode='lines', line=dict(width=0),legendgroup=titles[i], showlegend=False, hoverinfo='skip'), row=1, col=2)
            fig.add_trace(go.Scatter(x=r, y=PUncert[:,1], mode='lines', line=dict(width=0,color=colour_scheme_light[i]),legendgroup=titles[i], fill='tonexty', name='95% CI'), row=1, col=2)
    return fig

def plotly_deerlab(fitresult=None, orientation='h'):

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if orientation == 'h':
        fig = make_subplots(rows=1, cols=2, subplot_titles=["Time Domain", "Distance Distribution"], horizontal_spacing=0.1)
        fig.update_xaxes(title_text="Time (µs)", row=1, col=1)
        fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
        fig.update_xaxes(title_text="Distance (nm)", row=1, col=2)
        fig.update_yaxes(title_text="P(r) (nm⁻¹)", row=1, col=2)

    else:
        fig = make_subplots(rows=2, cols=1, subplot_titles=["Time Domain", "Distance Distribution"], vertical_spacing=0.1)
        fig.update_xaxes(title_text="Time (µs)", row=1, col=1)
        fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
        fig.update_xaxes(title_text="Distance (nm)", row=2, col=1)
        fig.update_yaxes(title_text="P(r) (nm⁻¹)", row=2, col=1)

    
    if fitresult is None:
        return fig
    
    if isinstance(fitresult, dl.FitResult):
        data_t = fitresult.t
        data_V = fitresult.Vexp
        if hasattr(fitresult,'model_t'):
            model_t = fitresult.model_t
        else:
            model_t = data_t
        data_model = fitresult.model
        P = fitresult.P
        PUncert = fitresult.PUncert.ci(95)
        r = fitresult.r
    elif isinstance(fitresult,xr.DataArray):
        data_t = fitresult.t.values
        data_V = fitresult.values
        data_V = data_V.real
        data_V = data_V / np.max(np.abs(data_V))
        data_model = None
        P = None
        PUncert = None
        r = None
    elif isinstance(fitresult, dict):
        data_t = fitresult['t']
        data_V = fitresult['V']
        data_model = fitresult['model'] if 'model' in fitresult else None
        if hasattr(fitresult,'model_t'):
            model_t = fitresult['model_t']
        else:
            model_t = data_t
        P = fitresult['P'] if 'P' in fitresult else None
        PUncert = fitresult['PUncert'] if 'PUncert' in fitresult else None
        r = fitresult['r'] if 'r' in fitresult else None
    else:
        raise ValueError("fitresult must be either a DeerLab FitResult object or an xarray DataArray, not {}".format(type(fitresult)))
    i=0
    fig.add_trace(go.Scatter(
            x=data_t, y=data_V, mode='markers', name='Data',
            line={'color':colour_scheme_light[i]}), row=1, col=1)
    if data_model is not None:
        fig.add_trace(go.Scatter(x=model_t, y=data_model, mode='lines', name='Model', line={'color':colour_scheme_dark[i]}), row=1, col=1)
    if P is not None:
        fig.add_trace(go.Scatter(x=r, y=P, mode='lines', name='P(r)', line={'color':colour_scheme_dark[i]}), row=1, col=2)
    if PUncert is not None:
        fig.add_trace(go.Scatter(x=r, y=PUncert[:,0], mode='lines', line=dict(width=0),showlegend=False, hoverinfo='skip'), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=PUncert[:,1], mode='lines', line=dict(width=0,color=colour_scheme_light[i]), fill='tonexty', name='95% CI'), row=1, col=2)
        
    return fig
    

def fit_to_dict(fit):
    """Takes a fit objects and converts it to a dictionary for storage in the database."""
    output = {}
    if isinstance(fit, dl.FitResult):
        if hasattr(fit, 'Bmodel'):
            output['engine'] = 'DeerLab'
            output['bg_model'] = fit.Bmodel.name if fit.Bmodel else None
            if hasattr(fit, 'Pmodel') and fit.Pmodel is not None:
                output['fit_type'] = 'parametric'
                output['dist_model'] = fit.Pmodel.name
            else:
                output['fit_type'] = 'non-parametric'
                output['dist_model'] = None
            output['pathways'] = fit.Vmodel.pathways
        else:
            output['bg_model'] = 'Neural Network'
            output['fit_type'] = 'Neural Network'
            output['engine'] = 'DeerNet'
            output['dist_model'] = None
            output['pathways'] = [1]

    output['t'] = fit.t.tolist() if fit.t is not None else None
    output['model'] = fit.model.tolist() if fit.model is not None else None
    output['P_model'] = fit.P.tolist() if fit.P is not None else None
    
    output['r'] = fit.r.tolist() if fit.r is not None else None
    output['PUncert'] = None
    output['model_description'] = fit.__str__() if fit is not None else None
    return output
    
    
def dists_stats_to_list(dist_stats, dist_uncert,ci=95):
    """Converts the distance distribution statistics to a list of dictionaries for display in the table."""
    stats = list(dist_stats.keys())

    Output = []
    for stat in stats:
        row = []
        key = stat
        row.append(stat)
        if isinstance(dist_stats[stat], (int, float)):

            row.append(f"{dist_stats[stat]:.3f}")
        elif isinstance(dist_stats[stat], (list, np.ndarray)):
            row.append(", ".join([f"{x:.3f}" for x in dist_stats[stat]]))
            
        if dist_uncert is not None and key in dist_uncert and dist_uncert[key] is not None:
            lb,ub = dist_uncert[key].ci(ci)
            row.append(f"[{lb:.3f}, {ub:.3f}]")
        else:
            row.append("N/A")
        Output.append(row)
    return Output

def name_dataset_from_dict(dataset_dict):
    """Creates a name for the fit based on the dataset and fit parameters."""
    
    if dataset_dict['fit_type'] == 'Neural Network':
        el1 = f"DeerNet"
    elif dataset_dict['fit_type'] == 'parametric':
        el1 = f"{dataset_dict['dist_model']}"
    else:
        el1 = f"Non-Parametric"

    if dataset_dict['pathways'] is not None:
        el2 = str([f"{p}" for p in dataset_dict['pathways']])
    else:
        el2 = ""

    return f"{el1}-{el2}"
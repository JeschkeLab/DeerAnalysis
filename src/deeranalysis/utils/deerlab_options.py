import deerlab as dl
import plotly.graph_objs as go
import plotly.express.colors as colors
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
     {"label": "Single Pathway", "value": "single", "max_pathways": 1, "delays": []},
    {"label": "4-pulse DEER", "value": "4pDEER", "max_pathways": 4, "delays": ['tau1', 'tau2']},
    {"label": "3-pulse DEER", "value": "3pDEER", "max_pathways": 3, "delays": ['tau1']},
    {"label": "5-pulse DEER", "value": "5pDEER", "max_pathways": 5, "delays": ['tau1', 'tau2', 'tau3']},
    {"label": "RIDME", "value": "RIDME","max_pathways": 4, "delays": ['tau1', 'tau2']},
    {"label": "SIFTER", "value": "SIFTER","max_pathways": 3, "delays": ['tau1', 'tau2']},
    {"label": "DQC", "value": "DQC","max_pathways": 3, "delays": ['tau1', 'tau2', 'tau3']},
    ]

background_models = [
    {'label': 'None', 'value': 'none'},
    {'label': 'Hom. 3D', 'value': 'bg_hom3d'},
    {'label': 'Hom. 3D - Excl. Vol.', 'value': 'bg_hom3dex'},
    {'label': 'Hom. Fractal Geom.', 'value': 'bg_homfractal'},
    # These models require complex input data which is not currently supported by the app, so they are commented out for now. They can be added back in the future if complex data support is added.
    # {'label': 'Hom. 3D - Phase shift', 'value': 'bg_hom3d_phase'},
    # {'label': 'Hom. 3D - Excl. Vol.,  Phase shift', 'value': 'bg_hom3dex_phase'},
    # {'label': 'Hom. Fractal Geom., Phase shift', 'value': 'bg_homfractal_phase'},    
    {'label': 'Exponential', 'value': 'bg_exp'},
    {'label': 'Stretched Exponential', 'value': 'bg_strexp'},
    {'label': 'Sum of 2 Stretched Exp.', 'value': 'bg_sumstrexp'},
    {'label': 'Prod of 2 Stretched Exp.', 'value': 'bg_prodstrexp'},
    {'label': '1st order polynomial.', 'value': 'bg_poly1'},
    {'label': '2nd order polynomial.', 'value': 'bg_poly2'},
    {'label': '3rd order polynomial.', 'value': 'bg_poly3'},
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
colour_scheme_dark = ['#7C37DB','#DB7C17','#166122','#1785DB','#DB1766']
colour_scheme_light = ['#A787D6',"#EDA659",'#67B875','#6BB5E8','#E867A8']



def resolve_plot_template(color_scheme=None, plot_theme=None):
    """
    Returns the Plotly template string to use based on the UI color scheme
    and the user's explicit plot theme preference.

    If plot_theme is "auto" or None, the template follows the UI color scheme
    (plotly_dark for dark mode, plotly_white for light mode).
    Otherwise, the user-chosen theme is used as-is, combined with the compact
    layout adjustments defined at app startup.
    """
    if plot_theme and plot_theme != "auto":
        return f"{plot_theme}+compact"
    return "plotly_dark+compact" if color_scheme == "dark" else "plotly_white+compact"

def plotly_goodness_of_fit(results=None, index=None):
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

    idx = index if index is not None else 0
    t         = results.t[idx]         if isinstance(results.t, list)         else results.t
    residuals = results.residuals[idx] if isinstance(results.residuals, list) else results.residuals
    noiselvl  = results.noiselvl[idx]  if isinstance(results.noiselvl, (list,np.ndarray))  else results.noiselvl

    data_color =  colour_scheme_light[0] #"#3409b6"  # Default plotly blue
    grey_color = "#ACACAC"  # Grey for confidence intervals

    # Plot 1: Residuals with noise level and mean
    fig.add_trace(go.Scatter(x=t, y=residuals, mode='markers', name='Residuals', line={'color':data_color}), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=2*noiselvl*np.ones_like(t), mode='lines', name='2σ', line=dict(dash='dash',color=grey_color),showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=-2*noiselvl*np.ones_like(t),fill='tonexty', mode='lines', name='±2σ', line=dict(color=grey_color)), row=1, col=1)
    # fig.add_trace(go.Scatter(x=results.dataset.t, y=np.mean(results.residuals)*np.ones_like(results.dataset.t), mode='lines', name='Mean', line=dict(dash='dot')), row=1, col=1)
    fig.update_xaxes(title_text="Time (µs)", row=1, col=1)

    # Plot 2: Histogram of residuals with normal distribution fit
    norm_residuals = (residuals - np.mean(residuals)) / np.std(residuals)
    hist_data = np.histogram(norm_residuals, bins=20,range=(-4,4), density=True)
    x_hist = (hist_data[1][:-1] + hist_data[1][1:]) / 2  # Bin centers
    x = np.linspace(-4, 4, 100)
    y_hist = hist_data[0]
    fig.add_trace(go.Bar(x=x_hist, y=y_hist, name='Residuals',marker={'color':data_color}), row=1, col=2)
    fig.add_trace(go.Scatter(x=x, y=(1/np.sqrt(2*np.pi))*np.exp(-0.5*x**2), mode='lines', name='Normal Fit', showlegend=True), row=1, col=2)
    fig.update_yaxes(visible=False, row=1, col=2)

    fig.update_xaxes(range=[-4, 4],title_text="Normalized Residuals", row=1, col=2)


    # Plot 3: Autocorrelation of residuals with confidence intervals
    maxLag = len(norm_residuals)-1
    acorr = np.correlate(residuals, residuals, mode='full')
    #normed
    acorr = acorr / np.dot(residuals, residuals)
    lags = np.arange(-len(residuals)+1, len(residuals))
    acorr = acorr[lags>-0.5]
    lags = lags[lags>-0.5]
    fig.add_trace(go.Scatter(x=lags, y=acorr, mode='lines', name='Residuals', line={'color':data_color}), row=1, col=3)
    threshold = 1.96/np.sqrt(len(residuals))
    fig.add_trace(go.Scatter(x=lags, y=threshold*np.ones_like(lags), fill=None, mode='lines', line=dict(color=grey_color),showlegend=False), row=1, col=3)
    fig.add_trace(go.Scatter(x=lags, y=-threshold*np.ones_like(lags), fill='tonexty', mode='lines', name='White Noise Confidence Region', line=dict(color=grey_color)), row=1, col=3,)

    # Set lower x lim
    fig.update_xaxes(range=[-0.5, maxLag],title_text="Lags", row=1, col=3)
    fig.update_yaxes(visible=False, row=1, col=3)


    return fig


def plotly_comparison(results, titles=None, offset=0.3, ci=95, show_ci=True):
    """
    Compares multiple fits or datasets by plotting their time domain data and distance distributions
    in a single plotly figure with two subplots.

    Parameters
    ----------
    results : list of dl.FitResult or dict
        Each dict should have keys: 't', 'V', 'model', 'r', 'P', optionally 'PUncert'.
    titles : list of str, optional
    offset : float
        Vertical spacing between adjacent datasets in the time domain plot.
    ci : int
        Confidence interval percentage to display (e.g. 95).
    show_ci : bool
        Whether to show the uncertainty bands on the distance distribution.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Time Domain", "Distance Distribution"], horizontal_spacing=0.1,)
    
    # If no fits provided, return empty figure with titles
    if results is None or len(results) == 0:
        return fig
    
    if titles is None:
        titles = [f"Fit {i+1}" for i in range(len(results))]

    # Set axes labels
    fig.update_xaxes(title_text="Time (µs)", row=1, col=1)
    fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
    fig.update_xaxes(title_text="Distance (nm)", row=1, col=2)
    fig.update_yaxes(title_text="P(r) (nm⁻¹)", row=1, col=2)

    vspacing = np.arange(len(results)) * offset

    for i, res in enumerate(results):
        if isinstance(res, dl.FitResult):
            data_t = res.dataset.t.values
            data_V = res.Vexp + vspacing[i]
            data_model = res.model + vspacing[i]
            PUncert = res.PUncert.ci(ci) if show_ci else None
            r = res.r
            P = res.P
            model_t = res.model_t if hasattr(res,'model_t') else data_t
            background = res.background if hasattr(res,'background') else None
        elif isinstance(res, dict):
            data_t = res['t']
            data_V = res['V'] + vspacing[i]
            data_model = res['model'] + vspacing[i]
            r = res['r']
            P = res['P']
            if 'PUncert' in res and res['PUncert'] is not None and show_ci:
                if isinstance(res['PUncert'], dl.UQResult):
                    PUncert = res['PUncert'].ci(ci)
                else:
                    PUncert = res['PUncert']
            else:
                PUncert = None
            model_t = res['model_t'] if 'model_t' in res else data_t
            background = res['background'] if 'background' in res else None
        else:
            raise ValueError("Each fit result must be either a dl.FitResult, xr.DataArray or a dict. Invalid type: {}".format(type(res)))
        
        if len(model_t) != len(data_model):
            raise ValueError(f"Length of model_t ({len(model_t)}) does not match length of data_model ({len(data_model)}). Please ensure that model_t and model have the same length.")
        fig.add_trace(go.Scatter(
            x=data_t, y=data_V, mode='markers', name='Data',
            legendgroup=titles[i], legendgrouptitle_text=titles[i],
            marker={'color': colour_scheme_light[i]}), row=1, col=1)
        if background is not None:
            fig.add_trace(go.Scatter(x=model_t, y=background, mode='lines', name='Background', line={'color':colour_scheme_dark[i],'dash':'dash'}), row=1, col=1)
        fig.add_trace(go.Scatter(x=model_t, y=data_model, mode='lines', name='Model', legendgroup=titles[i], line={'color': colour_scheme_dark[i]}), row=1, col=1)

        fig.add_trace(go.Scatter(x=r, y=P, mode='lines', name='P(r)', legendgroup=titles[i], line={'color': colour_scheme_dark[i]}), row=1, col=2)
        if PUncert is not None:
            ci_label = f"{ci}% CI"
            fig.add_trace(go.Scatter(x=r, y=PUncert[:, 0], mode='lines', line=dict(width=0), legendgroup=titles[i], showlegend=False, hoverinfo='skip'), row=1, col=2)
            fig.add_trace(go.Scatter(x=r, y=PUncert[:, 1], mode='lines', line=dict(width=0, color=colour_scheme_light[i]), legendgroup=titles[i], fill='tonexty', name=ci_label), row=1, col=2)

    return fig

def plotly_deerlab(fitresult=None, orientation='h', index=None,
                    showPathways=False, showPopulation=False,linewidth=3):

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

    Ps_pop   = None
    UQs_pop  = None
    P_factor = 1.0

    if isinstance(fitresult, dl.FitResult):
        idx = index if index is not None else 0
        
        data_t     = fitresult.t[idx]     if isinstance(fitresult.t, list)     else fitresult.t
        data_V     = fitresult.Vexp[idx]  if isinstance(fitresult.Vexp, list)  else fitresult.Vexp
        pathways = fitresult.pathways if hasattr(fitresult,'pathways') else None
        model_t    = data_t
        if pathways is not None:
            data_model = fitresult.model[idx] if isinstance(fitresult.model, list) else fitresult.model
            r          = fitresult.r
        else:
            data_model = None
            r           = None
        if (hasattr(fitresult,'background') and isinstance(fitresult.background, list)):
            background = fitresult.background[idx]  
        elif hasattr(fitresult,'background'): 
            background = fitresult.background
        else:
            None

        if hasattr(fitresult, 'P') and isinstance(fitresult.P, list) and fitresult.P is not None:
            P  = fitresult.P[idx]
            PUncert = fitresult.PUncert[idx]
            if isinstance(P, dict) and 'sum' in P:
                Ps_pop = P
                P = P['sum']
                if hasattr(fitresult, 'PUQ'):
                    UQs_pop = PUncert['UQs']
                    P_factor = PUncert['factor']
                else:
                    UQs_pop = None
                    P_factor = 1.0
                PUncert = UQs_pop['sum'] if UQs_pop is not None else None
        elif hasattr(fitresult, 'P'):
            P       = fitresult.P
            PUncert = fitresult.PUncert.ci(95) if hasattr(fitresult,'PUncert') else None
        else:
            print("Warning: FitResult does not contain P or PUQ attributes. Distance distribution will not be plotted.")
            P = None
            PUncert = None

        if hasattr(fitresult,"mod") and showPathways:
            raise ValueError("showPathway requires multi-pathway fitting")
        elif hasattr(fitresult,"pathways") and showPathways and not showPopulation:
            if len(fitresult.pathways)==1:
                lams = [getattr(fitresult,f"mod")]
                reftimes = [getattr(fitresult,f"reftime")]
            else:
                lams           = [getattr(fitresult,f"lam{i}") for i in fitresult.pathways]
                reftimes       = [getattr(fitresult,f"reftime{i}") for i in fitresult.pathways]
            pathway_labels = [f'Pathway #{i}' for i in fitresult.pathways]
            cmap           = colors.qualitative.T10
        elif hasattr(fitresult,"pathways") and showPathways and showPopulation:
            if len(fitresult.pathways[idx])==1:
                lams = [getattr(fitresult,f"mod_{idx+1}")]
                reftimes = [getattr(fitresult,f"reftime_{idx+1}")]
            else:
                lams           = [getattr(fitresult,f"lam{i}_{idx+1}") for i in fitresult.pathways[idx]]
                reftimes       = [getattr(fitresult,f"reftime{i}_{idx+1}") for i in fitresult.pathways[idx]]
            pathway_labels = [f'Pathway #{i}' for i in fitresult.pathways[idx]]
            cmap           = colors.qualitative.T10

    elif isinstance(fitresult,xr.DataArray):
        n_fits = 1
        data_t = fitresult.t.values
        data_V = fitresult.values
        data_V = data_V.real
        data_V = data_V / np.max(np.abs(data_V))
        data_model = None
        P = None
        PUncert = None
        r = None
        background = None
    elif isinstance(fitresult, dict):
        idx = index if index is not None else 0
        data_t = fitresult['t'][idx] if isinstance(fitresult['t'], list) else fitresult['t']
        data_V = fitresult['V'][idx] if isinstance(fitresult['V'], list) else fitresult['V']
        data_model = fitresult['model'] if 'model' in fitresult else None
        if 'model_t' in fitresult and fitresult['model_t'] is not None:
            model_t = fitresult['model_t'][idx] if isinstance(fitresult['model_t'], list) else fitresult['model_t']
        else:
            model_t = data_t
        P = fitresult['P'] if 'P' in fitresult else None
        if 'PUncert' in fitresult and fitresult['PUncert'] is not None:
            if isinstance(fitresult['PUncert'], dl.UQResult):
                PUncert = fitresult['PUncert'].ci(95)
            else:
                PUncert = fitresult['PUncert']
        else:
            PUncert = None
        r = fitresult['r'] if 'r' in fitresult else None
        background = fitresult['background'] if 'background' in fitresult else None
    else:
        raise ValueError("fitresult must be either a DeerLab FitResult object or an xarray DataArray, not {}".format(type(fitresult)))
    i=0
    fig.add_trace(go.Scatter(
            x=data_t, y=data_V, mode='markers', name='Data',
            line={'color':colour_scheme_light[i], 'width':linewidth}), row=1, col=1)
    if background is not None:
        fig.add_trace(go.Scatter(x=model_t, y=background, mode='lines', name='Background', line={'color':colour_scheme_dark[i],'dash':'dash', 'width':linewidth}), row=1, col=1)
    
    if data_model is not None and not showPathways:
        fig.add_trace(go.Scatter(x=model_t, y=data_model, mode='lines', name='Model', line={'color':colour_scheme_dark[i], 'width':linewidth}), row=1, col=1)
    elif data_model is not None and background is not None:
        for (lam,reftime,c,label) in zip(lams,reftimes,cmap,pathway_labels):
            Vpath = (1-np.sum(lams)+lam*dl.dipolarkernel(model_t-reftime,r)@P) * (background/(1-np.sum(lams)))
            fig.add_trace(go.Scatter(x=model_t,y=Vpath,mode='lines',name=label,line={'color':c, 'width':linewidth}),row=1,col=1)
    elif data_model is not None and background is None:
        for (lam,reftime,c,label) in zip(lams,reftimes,cmap,pathway_labels):
            Vpath = (1-np.sum(lams)+lam*dl.dipolarkernel(model_t-reftime,r)@P)
            fig.add_trace(go.Scatter(x=model_t,y=Vpath,mode='lines',name=label,line={'color':c, 'width':linewidth}),row=1,col=1)

    if P is not None and showPopulation and Ps_pop is not None:
        pop_letters = [k for k in Ps_pop if k != 'sum']
        for letter in pop_letters:
            fig.add_trace(go.Scatter(x=r, y=Ps_pop[letter], mode='lines', name=f'Pop. {letter}',line={'width':linewidth}), row=1, col=2)
            color = fig.data[-1].line.color
            if UQs_pop is not None and letter in UQs_pop:
                ci_pop = UQs_pop[letter].ci(95) * P_factor
                fig.add_trace(go.Scatter(x=r, y=ci_pop[:,0], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=2)
                fig.add_trace(go.Scatter(x=r, y=ci_pop[:,1], mode='lines', line=dict(width=0, color=color), fill='tonexty', showlegend=True, hoverinfo='skip', name='95% CI'), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=P, mode='lines', name='Sum', line={'color': colour_scheme_dark[i]}), row=1, col=2)
    elif P is not None:
        fig.add_trace(go.Scatter(x=r, y=P, mode='lines', name='P(r)', line={'color':colour_scheme_dark[i],'width':linewidth}), row=1, col=2)
    if PUncert is not None:
        ci = (PUncert.ci(95) * P_factor) if isinstance(PUncert, dl.UQResult) else PUncert
        fig.add_trace(go.Scatter(x=r, y=ci[:,0], mode='lines', line=dict(width=0),showlegend=False, hoverinfo='skip'), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=ci[:,1], mode='lines', line=dict(width=0,color=colour_scheme_light[i]), fill='tonexty', name='95% CI'), row=1, col=2)
        
    return fig
    

def fit_to_dict(fit,background_only=False):
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

            if hasattr(fit,'background') and fit.background is not None:
                output['background'] = fit.background.tolist()
            elif hasattr(fit,'Bmodel') and fit.background is None:
                output['background'] = None
            if background_only:
                output['pathways'] = None
            else:
                output['pathways'] = fit.Vmodel.pathways
        else:
            output['bg_model'] = 'Neural Network'
            output['fit_type'] = 'Neural Network'
            output['engine'] = 'DeerNet'
            output['dist_model'] = None
            output['pathways'] = [1]

    output['t'] = fit.t.tolist() if fit.t is not None else None
    output['model'] = fit.model.tolist() if fit.model is not None else None
    if background_only:
        output['P_model'] = None
        output['r'] = None
        output['PUncert'] = None
    else:
        output['P_model'] = fit.P.tolist() if fit.P is not None else None
        output['r'] = fit.r.tolist() if fit.r is not None else None
        output['PUncert'] = fit.PUncert.to_dict() if fit.PUncert is not None else None
    output['model_description'] = fit.__str__() if fit is not None else None
    output['data'] = dl.json_dumps(fit) if fit is not None else None
    return output
    
    
# def dists_stats_to_list(dist_stats, dist_uncert,ci=95):
#     """Converts the distance distribution statistics to a list of dictionaries for display in the table."""
#     stats = list(dist_stats.keys())

#     Output = []
#     for stat in stats:
#         row = []
#         key = stat
#         row.append(stat)
#         if isinstance(dist_stats[stat], (int, float)):

#             row.append(f"{dist_stats[stat]:.3f}")
#         elif isinstance(dist_stats[stat], (list, np.ndarray)):
#             row.append(", ".join([f"{x:.3f}" for x in dist_stats[stat]]))
            
#         if dist_uncert is not None and key in dist_uncert and dist_uncert[key] is not None:
#             lb,ub = dist_uncert[key].ci(ci)
#             row.append(f"[{lb:.3f}, {ub:.3f}]")
#         else:
#             row.append("N/A")
#         Output.append(row)
#     return Output

def dists_stats_to_list(dist_stats, dist_uncert, ci=95):
    """Converts distance distribution statistics to a JSON-serializable dict of key scalar statistics."""
    KEY_STATS = ['mean', 'median', 'mode', 'std', 'iqr', 'skewness', 'kurtosis']
    output = {}
    for key in KEY_STATS:
        if key not in dist_stats:
            continue
        val = dist_stats[key]
        entry = {'value': float(val)}
        if dist_uncert is not None and key in dist_uncert and dist_uncert[key] is not None:
            lb, ub = dist_uncert[key].ci(ci)
            entry['ci'] = [float(lb), float(ub)]
        else:
            entry['ci'] = None
        output[key] = entry
    return output

def name_dataset_from_dict(dataset_dict):
    """Creates a name for the fit based on the dataset and fit parameters."""

    if dataset_dict['fit_type'] == 'Neural Network':
        el1 = f"DeerNet"
    elif dataset_dict['fit_type'] == 'parametric':
        el1 = f"{dataset_dict['dist_model']}"
    elif dataset_dict['fit_type'] == 'Population':
        el1 = f"Population Fit"
    else:
        el1 = f"Non-Parametric"

    if dataset_dict['pathways'] is not None:
        el2 = str([f"{p}" for p in dataset_dict['pathways']])
    else:
        el2 = ""

    return f"{el1}-{el2}"


def _safe_float(val):
    """Convert a possibly-array / possibly-inf value to a Python float, or None."""
    if val is None:
        return None
    try:
        v = float(np.atleast_1d(val)[0])
        return v if np.isfinite(v) else None
    except Exception:
        return None


def build_model_data(dataset, bg_model_name, pathways, r_range,
                     p_model_name=None, existing_overrides=None, p_model=None):
    """
    Build a serialisable dict of the dipolar model parameters for the modal.

    Parameters
    ----------
    dataset : xarray.DataArray
        Loaded dataset (must have .t coords and .attrs with tau values).
    bg_model_name : str or None
        DeerLab background model name (e.g. ``'bg_hom3d'``) or ``'none'``.
    pathways : list of int
        Pathway indices to include.
    r_range : list of float
        [r_min, r_max] in nm.
    p_model_name : str or None
        DeerLab distance-distribution model name (e.g. ``'dd_gauss'``).
        ``None`` → non-parametric (model-free) fit.
    existing_overrides : dict or None
        Previously saved parameter overrides (``model-params-store`` data).
        Values for params that still exist in the new model are preserved so
        that changing background model or pathways does not reset unaffected
        parameters.

    Returns
    -------
    dict with keys ``'params'``, ``'exp_type'``, ``'bg_model'``,
    ``'p_model'``, ``'pathways'``.
    """
    t = dataset.t.values
    if t.max() > 500:
        t = t / 1e3  # ns → µs

    r = np.linspace(r_range[0], r_range[1], 100)
    attrs = dataset.attrs
    seq_name = attrs.get('seq_name', '')

    if seq_name == '5pDEER' or ('tau3' in attrs and seq_name != '4pDEER'):
        exp_type = '5pDEER'
        tau1 = attrs['tau1'] / 1e3
        tau2 = attrs['tau2'] / 1e3
        tau3 = attrs['tau3'] / 1e3
        pathways = [p for p in pathways if p <= 5]
        exp_info = dl.ex_fwd5pdeer(tau1, tau2, tau3, pathways=pathways)
    elif seq_name == '3pDEER':
        exp_type = '3pDEER'
        tau1 = attrs['tau1'] / 1e3
        pathways = [p for p in pathways if p <= 2]
        exp_info = dl.ex_3pdeer(tau=tau1, pathways=pathways)
    else:
        # Default / 4pDEER
        exp_type = '4pDEER'
        tau1 = attrs.get('tau1', 400) / 1e3
        tau2 = attrs.get('tau2', 2400) / 1e3
        pathways = [p for p in pathways if p <= 4]
        exp_info = dl.ex_4pdeer(tau1, tau2, pathways=pathways)

    bg_model = (
        getattr(dl, bg_model_name, None)
        if bg_model_name and bg_model_name != 'none'
        else None
    )
    if p_model is None:
        p_model = getattr(dl, p_model_name, None) if p_model_name else None

    Vmodel = dl.dipolarmodel(t, r, experiment=exp_info,
                             Bmodel=bg_model, Pmodel=p_model)

    params_dict = {}
    for name in Vmodel.signature:
        if name in ('t', 'P'):
            continue
        try:
            param = getattr(Vmodel, name)
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

    # Preserve user overrides for parameters that still exist in the new model
    if existing_overrides:
        for name, override in existing_overrides.items():
            if name in params_dict:
                for key in ('par0', 'lb', 'ub', 'frozen'):
                    if key in override and override[key] is not None:
                        params_dict[name][key] = override[key]

    return {
        'params': params_dict,
        'exp_type': exp_type,
        'bg_model': bg_model_name,
        'p_model': p_model_name,
        'pathways': pathways,
    }


def plotly_lcurve(fitresult=None, orientation='h'):
    """Returns a plotly figure with the L-curve data and the selected regularization parameter."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots



    if orientation == 'h':
        fig = make_subplots(rows=1, cols=2, subplot_titles=[r"α selection functional", "L-Curve"], horizontal_spacing=0.1)
        fig.update_xaxes(title_text="α Regularisation Parameter", type='log', row=1, col=1)
        fig.update_yaxes(title_text="Functional Value", row=1, col=1)
        fig.update_xaxes(title_text=r"||Kx - y||₂ (Residual Norm)", type='log', row=1, col=2)
        fig.update_yaxes(title_text=r"||Lx||₂ (Solution Norm)", type='log', row=1, col=2)
    else:
        fig = make_subplots(rows=2, cols=1, subplot_titles=[r"α selection functional", "L-Curve"], vertical_spacing=0.1)
        fig.update_xaxes(title_text="α Regularisation Parameter", type='log', row=1, col=1)
        fig.update_yaxes(title_text="Functional Value", row=1, col=1)
        fig.update_xaxes(title_text=r"||Kx - y||₂ (Residual Norm)", type='log', row=2, col=1)
        fig.update_yaxes(title_text=r"||Lx||₂ (Solution Norm)", type='log', row=2, col=1)

    if fitresult is None or not hasattr(fitresult, 'regparam_stats'):
        return fig
    
    alphas = fitresult.regparam_stats['alphas_evaled'][1:]
    funcs = fitresult.regparam_stats['functional'][1:]

    res = fitresult.regparam_stats['residuals']
    pens = fitresult.regparam_stats['penalties']

    # Sort functional by alphas
    sort_idx_func = np.argsort(alphas)
    alphas = alphas[sort_idx_func]
    funcs = funcs[sort_idx_func]

    # Sort L-curve by residuals
    sort_idx_lcurve = np.argsort(res)
    res = res[sort_idx_lcurve]
    pens = pens[sort_idx_lcurve]
    alphas_lcurve = fitresult.regparam_stats['alphas_evaled'][sort_idx_lcurve]


    r1, c1 = (1, 1)
    r2, c2 = (1, 2) if orientation == 'h' else (2, 1)

    fig.add_trace(go.Scatter(x=alphas, y=funcs, mode='lines+markers', name='Functional', line={'color':colour_scheme_dark[0]}), row=r1, col=c1)
    fig.add_trace(
        go.Scatter(x=res, y=pens, mode='lines+markers', name='L-Curve', line={'color':colour_scheme_dark[1]},
                    customdata=alphas_lcurve,hovertemplate='||Kx - y||₂: %{x:.3e}   ||Lx||₂: %{y:.3e}. α: %{customdata:.3e}')
                , row=r2, col=c2)
    # Highlight the selected regularisation parameter on both plots
    selected_alpha = fitresult.regparam
    selected_idx = np.argmin(np.abs(alphas - selected_alpha))
    selected_idx_lcurve = np.argmin(np.abs(alphas_lcurve - selected_alpha))

    fig.add_trace(go.Scatter(x=[alphas[selected_idx]], y=[funcs[selected_idx]], mode='markers', name='Selected α', marker=dict(color=colour_scheme_light[0], size=10, symbol='x')), row=r1, col=c1)
    fig.add_trace(go.Scatter(
            x=[res[selected_idx_lcurve]], y=[pens[selected_idx_lcurve]], mode='markers', name='Selected α',
            marker=dict(color=colour_scheme_light[1], size=10, symbol='x'),
            customdata=[alphas_lcurve[selected_idx_lcurve]],
            hovertemplate='Residual Norm: %{x:.3e}<br>Solution Norm: %{y:.3e}<br>α: %{customdata:.3e}<extra></extra>'
        ), row=r2, col=c2)
    return fig
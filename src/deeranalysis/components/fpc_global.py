# --------------------------------------------------------------
# Fit-page components related to global fitting of multiple datasets
# --------------------------------------------------------------

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_options import regparam_options, plotly_deerlab, plotly_goodness_of_fit,plotly_lcurve
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils import dataarray_from_database_entry
from deeranalysis.utils.deerlab_population import determine_pop_P

from dash import dcc, html, callback, Input, Output, State, MATCH
import deerlab as dl
import numpy as np

# --------------------------------------------------------------
# Main figure pagation component for global fits
# --------------------------------------------------------------

def plotly_deerlab_pagination(page_id,show_population_option=False):
    """
    For globally fit datasets, creates a plotly figure using the plotly deerlab function for each dataset and combines them
    into a single element with a dmc.Pagination component to navigate between them. This is encapsulated in a dmc.Paper just like the fit_plot function. 
    The pagination component will have as many pages as there are datasets, and the figure will update to show the corresponding dataset when a page is selected.

    If no datasets are provided, returns a default plotly deerlab figure but still with a pagination element.
    """

    buttons =[]
    buttons.append(dmc.Switch(id={'type': 'fit-plot-multi-showpathways','page':page_id},
                             onLabel="ON", offLabel="OFF",
                             label="Show Pathways:", labelPosition='left',
                             size="md",pr='lg'))
    if show_population_option:
        style=None
    else:
        style={"display": "none"}
    buttons.append(dmc.Switch(id={'type': 'fit-plot-multi-showpopulation','page':page_id},
                            onLabel="ON", offLabel="OFF",
                            label="Show Population:", labelPosition='left',
                            size="md",pr='lg',style=style))

    return dmc.Paper([
        dmc.Group([
            dmc.Text("Dataset:", size="md", id={"type": "fit-plot-multi-label", "page": page_id}, mb=0),
            dmc.Group(buttons),
        ],justify="space-between"),

        dcc.Graph(
            id={"type": "fit-plot-multi", "page": page_id},
            figure=plotly_deerlab(None),
            style={'height': '100%'},
            config={'responsive': True},
        ),
        dmc.Center(
            dmc.Pagination(
                id={"type": "fit-plot-pagination", "page": page_id},
                total=1,
                value=1,
                withEdges=True,
            ),
            mt="xs",
        ),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 300})


@callback(
    Output({"type": "fit-plot-multi", "page": MATCH}, "figure"),
    Output({'type': 'fit-plot-multi-showpathways', 'page': MATCH}, 'disabled'),
    Output({"type": "fit-plot-pagination", "page": MATCH}, "total"),
    Input({'type': 'fit-results-store-multi', 'page': MATCH}, 'data'),
    Input({'type': 'fit-plot-multi-showpathways', 'page': MATCH}, 'checked'),
    Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
    Input({'type': 'fit-plot-multi-showpopulation', 'page': MATCH}, 'checked'),
    prevent_initial_call=True,
    allow_missing_callback_args=True,
)
def update_multi_fit_plot(fit_result_dict:dict, show_pathways, page_value, show_population=None):
    if fit_result_dict is None:
        return plotly_deerlab(None), True,1
    if 'data' not in fit_result_dict:
        if 'V' in fit_result_dict:
            n_fits = len(fit_result_dict['V'])
            return plotly_deerlab(fit_result_dict,index=page_value-1), True,n_fits
        else:
            return plotly_deerlab(None), True,1
    n_fits = len(fit_result_dict['V'])
    fit_result = dl.json_loads(fit_result_dict['data'])
    
    if n_fits == 0:
        print("Fit results data is empty.")
        return plotly_deerlab(None), True,1
    
    
    if not hasattr(fit_result, 'pathways') or len(fit_result.pathways) == 1:
        show_pathways = False
        pathway_option = False
    else:
        pathway_option = True

    dd_model_name = fit_result_dict.get('dist_model',None)
    if dd_model_name is not None and hasattr(dl, dd_model_name):
        dd_model = getattr(dl, dd_model_name)
    else:
        dd_model = None

    if fit_result_dict['fit_type'] == 'Population':
        n_pops = fit_result_dict.get('n_pops', 1)
        Ps, PUQs = determine_pop_P(fit_result.r,fit_result,dd_model,n_datasets=n_fits,n_pops=n_pops)
        fit_result.P = Ps
        fit_result.PUQ = PUQs
    return plotly_deerlab(fitresult=fit_result, showPathways=show_pathways or False, index=page_value-1, showPopulation=show_population), not pathway_option, n_fits
    

# --------------------------------------------------------------
# GOF pagation component for global fits
# --------------------------------------------------------------


def goodness_of_fit_tab_pagination(page_id):

    tabstab = dmc.TabsTab("Goodness of Fit", value="gof")
    panel = dmc.TabsPanel(value="gof", children=[
        
        dcc.Graph(
            id={"type": "gof-plot-multi", "page": page_id},
            figure=plotly_goodness_of_fit(),
            style={'height': '100%'},
            config={'responsive': True},
        ),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel

@callback(
    Output({"type": "gof-plot-multi", "page": MATCH}, "figure"),
    Input({'type': 'fit-results-store-multi', 'page': MATCH}, 'data'),
    Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def update_multi_gof_plot(fit_results_data:list,page_value):
    if fit_results_data is None:
        return plotly_goodness_of_fit()
    
    if 'data' not in fit_results_data:
        return plotly_goodness_of_fit()
    
    fit = dl.json_loads(fit_results_data['data'])
    fig = plotly_goodness_of_fit(results=fit,index=page_value-1)
    return fig

def dist_stats_tab_pagination(page_id):
    tabstab = dmc.TabsTab("Dist. Stats", value="dist-stats")

    panel =  dmc.TabsPanel(value="dist-stats", children=[
        dmc.Table(
            id={"type": "dist-stats-table-multi", "page": page_id},
            data={
                "head": ["Statistic", "Value", "Confidence Interval (95%)"],
            },
            striped=True,
            highlightOnHover=True,
        )
    ], style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'})
    return tabstab, panel

@callback(
    Output({"type": "dist-stats-table-multi", "page": MATCH}, "data"),
    Input({'type': 'fit-results-store-multi', 'page': MATCH}, 'data'),
    Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def update_multi_dist_stats_table(fit_results_data:list,page_value):
    if fit_results_data is None:
        return plotly_goodness_of_fit()
    
    if 'data' not in fit_results_data:
        return plotly_goodness_of_fit()
    
    fit = dl.json_loads(fit_results_data['data'])
    
    


# --------------------------------------------------------------
# Overview pagation component for population fits
# --------------------------------------------------------------

def _make_population_card_children(letter, percentage=None, pct_unc=None, mean=None, mean_unc=None, std=None, std_unc=None, color=None):
    """Builds the children for a population card. Used by population_card and update callbacks."""
    pct_str  = f"{percentage * 100:.1f}%" if percentage is not None else "N/A"
    pct_unc_str = f"± {pct_unc * 100:.1f}%" if pct_unc is not None else "± N/A"
    if color is None:
        color = "dimmed"

    def _val_unc(val, unc, unit="nm"):
        if val is None:
            return "N/A"
        s = f"{val:.3g}"
        if unc is not None:
            s += f" ± {unc:.2g}"
        return s + f" {unit}"

    return dmc.Group([
        dmc.Text(letter, fw=900, c=color, style={"fontSize": "3.5rem", "lineHeight": 1}),
        dmc.Stack([
            dmc.Text("⟨r⟩ = " + _val_unc(mean, mean_unc), size="sm", fw=500),
            dmc.Text("σ  = " + _val_unc(std,  std_unc),  size="sm", fw=500),
        ], gap=2, align="center"),
        dmc.Stack([
            dmc.Text(pct_str,     size="xl", fw=700),
            dmc.Text(pct_unc_str, size="sm", c="dimmed"),
        ], gap=2, align="center"),
    ], justify="space-between", align="center", px="xs")


def population_card(metric_id, page_id, percentage=None, pct_unc=None, mean=None, mean_unc=None, std=None, std_unc=None):
    """Creates a card showing population letter, mean/std (with uncertainties), and fractional weight."""
    letter = metric_id[-1].upper() if metric_id else "?"
    return dmc.Paper(
        _make_population_card_children(letter, percentage, pct_unc, mean, mean_unc, std, std_unc),
        id={"type": "population-card", "metric": metric_id, "page": page_id},
        withBorder=True,
        p="md",
        style={"minWidth": 200},
    )


def _safe_float(val):
    try:
        v = float(np.atleast_1d(val)[0])
        return v if np.isfinite(v) else None
    except Exception:
        return None



# @callback(
#     Output({"type": "overview-card", "metric": ALL, "page": MATCH}, "children", allow_duplicate=True),
#     Input({"type": "fit-results-store-multi", "page": MATCH}, "data"),
#     Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
#     prevent_initial_call=True,
# )
# def _update_population_gof_cards(store_data, page_value):
#     import dash
#     from deeranalysis.components.fit_page_components import METRIC_CONFIG, _make_card_children
#     outputs = dash.callback_context.outputs_list

#     if not store_data or store_data.get('fit_type') != 'Population' or 'data' not in store_data:
#         return [dash.no_update] * len(outputs)
#     try:
#         fit = dl.json_loads(store_data['data'])
#     except Exception:
#         return [dash.no_update] * len(outputs)

#     idx = (page_value or 1) - 1
#     stats = fit.stats[idx] if isinstance(fit.stats, (list, tuple)) and idx < len(fit.stats) else {}

#     lam = None
#     for attr in (f'lam1_{idx+1}', f'mod_{idx+1}'):
#         v = _safe_float(getattr(fit, attr, None))
#         if v is not None:
#             lam = v
#             break

#     metrics = {
#         'mnr':       {'value': _safe_float(stats.get('SNR')),     'uncertainty': None},
#         'chi2':      {'value': _safe_float(stats.get('chi2red')), 'uncertainty': None},
#         'rmsd':      {'value': _safe_float(stats.get('RMSD')),    'uncertainty': None},
#         'lambda':    {'value': lam,                                'uncertainty': None},
#         'mean_dist': {'value': None, 'uncertainty': None},
#         'std_dist':  {'value': None, 'uncertainty': None},
#     }

#     result = []
#     for out in outputs:
#         metric = out["id"]["metric"]
#         config = METRIC_CONFIG.get(metric, {"title": metric, "description": None, "thresholds": None})
#         m = metrics.get(metric, {})
#         result.append(_make_card_children(
#             title=config["title"],
#             value=m.get("value"),
#             uncertainty=m.get("uncertainty"),
#             description=config["description"],
#             thresholds=config["thresholds"],
#         ))
#     return result


@callback(
    Output({"type": "population-cards-grid", "page": MATCH}, "children"),
    Input({"type": "fit-results-store-multi", "page": MATCH}, "data"),
    Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def _update_population_cards(store_data, page_value):
    if not store_data or 'data' not in store_data:
        return []
    try:
        fit = dl.json_loads(store_data['data'])
    except Exception:
        return []

    import dash
    idx = (page_value or 1) - 1
    n_pops = store_data.get('n_pops', 2)
    pops = (store_data.get('populations') or [{}] * (idx + 1))[idx]
    page_id = dash.callback_context.outputs_list["id"]["page"]

    cards = []
    for j in range(n_pops):
        letter = chr(ord('A') + j)
        metric_id = f'pop{letter}'

        mean = _safe_float(getattr(fit, f'mean{letter}', None))
        std  = _safe_float(getattr(fit, f'std{letter}', None))
        meanUncert = getattr(fit, f'mean{letter}Uncert', None)
        stdUncert  = getattr(fit, f'std{letter}Uncert',  None)
        mean_unc = float(np.diff(meanUncert.ci(95))[0]) / 2 if meanUncert is not None else None
        std_unc  = float(np.diff(stdUncert.ci(95))[0])  / 2 if stdUncert  is not None else None

        pop_data = pops.get(letter, {}) if isinstance(pops, dict) else {}
        pct     = pop_data.get('frac')
        pct_unc = pop_data.get('unc')

        cards.append(population_card(
            metric_id, page_id,
            percentage=pct,  pct_unc=pct_unc,
            mean=mean,       mean_unc=mean_unc,
            std=std,         std_unc=std_unc,
        ))
    return cards


def overview_tab_population(page_id):
    """
    Creates the dash objects for the overview tab for the population. The content of the tab will change with the pagination. 
    Top row: MNR, Chi2, RMSD, Modulation Depth
    Bottom row: Population A, Population B, etc. depending on the number of populations fitted.
    """
    from deeranalysis.components.fit_page_components import overview_card

    tabstab = dmc.TabsTab("Overview", value="overview")
    panel = dmc.TabsPanel(value="overview", children=[
        # Dummy store so the shared overview-card callback can find all its MATCH inputs
        dcc.Store(id={"type": "fit-results-store", "page": page_id}),
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2, "lg": 4},
            mt="md",
            spacing="md",
            children=[
                overview_card("mnr",    page_id),
                overview_card("lambda", page_id),
                overview_card("chi2",   page_id),
                overview_card("rmsd",   page_id),
            ],
        ),
        dmc.Text("Population Metrics", size="lg", fw=700, mt="xl"),
        dmc.Space(h='md'),
        dmc.SimpleGrid(
            id={"type": "population-cards-grid", "page": page_id},
            cols={"base": 1, "sm": 2, "lg": 3},
            mb="md",
            spacing="md",
            children=[],
        ),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel

def overview_tab_global(page_id):
    """
    Creates the dash objects for the overview tab for the global fit. The content of the tab will change with the pagination. 
    Shows MNR, Chi2, RMSD, Modulation Depth for each dataset in the global fit.
    """
    from deeranalysis.components.fit_page_components import overview_card,_overview_card_grids

    tabstab = dmc.TabsTab("Overview", value="overview")
    panel = dmc.TabsPanel(value="overview", children=[
        # Dummy store so the shared overview-card callback can find all its MATCH inputs
        dcc.Store(id={"type": "fit-results-store", "page": page_id}),
        *_overview_card_grids(page_id),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel



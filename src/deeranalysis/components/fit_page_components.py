import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_options import regparam_options, plotly_deerlab, plotly_goodness_of_fit,plotly_lcurve,plotly_dipolar_spectrum
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils import dataarray_from_database_entry

from dash import dcc, html, callback, Input, Output, State, ALL, MATCH, no_update
import deerlab as dl
import numpy as np

DEFAULT_FIT_RESULTS_CODE = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

def fit_save_download_buttons(page_id):
    return dmc.Group([
            dmc.Button("Run Fit", id={"type":"run-fit-btn","page":page_id}, color="blue",variant='outline', className="mb-2 ms-1",leftSection=DashIconify(icon='material-symbols:play-arrow', width=20)),
            dmc.Button("Save Fit", id={"type":"save-fit-btn","page":page_id}, color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:save', width=20)),
            dmc.Button("Download", id={"type":"download-fit-btn","page":page_id}, color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:download', width=20)),
        ],gap="xs",)


def adv_fit_options_regularisation(page_id):

    return dmc.Accordion(
                    dmc.AccordionItem([
                        dmc.AccordionControl("Advanced Fit Options"),
                        dmc.AccordionPanel([
        dmc.Select(
            label='Regularization Method',
            description="Method for the automatic selection of the optimal regularization parameter:",
            id={"type": "regparam-method", "page": page_id},
            data=regparam_options,
            value='bic',
            clearable=False,
            allowDeselect=False,
        ),
        dmc.Select(
            label = 'Search Method', 
            description="Method for searching the optimal regularization parameter when using automatic selection",
            id={"type": "regparam-search-method", "page": page_id},
            data=[
                {"value": "brent", "label": "Brent Method"},
                {"value": "grid", "label": "Grid Search"},
                {'value': "fixed", "label": "Fixed Value"},
            ],
            value='brent',
            clearable=False,
            allowDeselect=False,
        ),
        dmc.NumberInput(
            label="Fixed Regularization Parameter (α):",
            id={"type": "fixed-alpha", "page": page_id},
            description="Set a fixed regularization parameter (overrides automatic selection)",
            type='text',
            value=0.1,
            step=0.001,
            allowNegative=False,
        ),
        dmc.NumberInput(
            label="Regularization Parameter Search Grid Size:",
            id={"type": "regparam-grid-size", "page": page_id},
            description="Number of points to evaluate when using grid search for automatic regularization parameter selection",
            value=60,
            step=5,
            min=10,
            disabled=True,
        ),

    ],)],value='adv-options'),)

@callback(
        Output({"type": "regparam-grid-size", "page": MATCH}, "disabled"),
        Output({"type": "fixed-alpha", "page": MATCH}, "disabled"),
        Input({"type": "regparam-search-method", "page": MATCH}, "value"),
        prevent_initial_call=False,
    )
def toggle_grid_size(search_method):
    return search_method != 'grid', search_method != 'fixed'

@callback(
    Output({"type": "regparam-search-method", "page": MATCH}, "data"),
    Output({"type": "regparam-search-method", "page": MATCH}, "value"),
    Input({"type": "regparam-method", "page": MATCH}, "value"),
    State({"type": "regparam-search-method", "page": MATCH}, "value"),
    prevent_initial_call=False,
)
def reg_param_search_method_options(criteria,current_search_method):
    if criteria in ['lr','lc']:
        options = [
            {"value": "grid", "label": "Grid Search"},
            {'value': "fixed", "label": "Fixed Value"},
        ]
    else:
        options = [
            {"value": "brent", "label": "Brent Method"},
            {"value": "grid", "label": "Grid Search"},
            {'value': "fixed", "label": "Fixed Value"},
        ]
    if current_search_method not in [opt['value'] for opt in options]:
        new_search_method = options[0]['value']
    else:        
        new_search_method = current_search_method
    return options, new_search_method


def adv_fit_options_parametric(page_id):
    return dmc.Group([
        dmc.NumberInput(label="Maximum Iterations:",
                        id={"type": "max-iter", "page": page_id},
                        value=1000,
                        step=1,
                        min=1,
                        className="mb-2"),
    ],gap="xs",)


def distance_slider(page_id):
    return dmc.Stack([dmc.Text("Distance Axis (nm): ", size="sm", fw=500, mb=4),
        dcc.RangeSlider(
                id= {"type": "distance-axis", "page": page_id},
                min=1.5,
                max=12,
                step=0.25,
                value=[1.75, 6],
                marks={i: f'{i}' for i in range(1, 13)},
                allowCross=False,
                allow_direct_input=True,
                className="dmc"
            )],gap=2,)


def fit_results_tab(page_id):
    """
    Creates the Fit Results tab panel for the fit results tabs. This will display the fit results code after running a fit.
    The panel contains a dmc.CodeHighlight component that will display the fit results as code after running the fit.
    
    Parameters:
    -----------
    page_id: string, the id of the page to use for the fit results code component

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Fit Results tab. 
    The TabsTab will have the label "Fit Results" and the TabsPanel will contain a dmc.CodeHighlight component with id {"type": "fit-results-code", "page": page_id} and default code set to DEFAULT_FIT_RESULTS_CODE.
    """

    tabstab = dmc.TabsTab("Fit Results", value="FitResults")

    panel =  dmc.TabsPanel(value="FitResults", children=[
        dmc.CodeHighlight(
            id={"type": "fit-results-code", "page": page_id},
            code=DEFAULT_FIT_RESULTS_CODE,
            language="plaintext",
            withCopyButton=True,
        )
    ], style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'})
    return tabstab, panel


def goodness_of_fit_tab(page_id):
    """
    Creates the Goodness of Fit tab panel for the fit results tabs. This will display a plot of goodness-of-fit metrics after running a fit.
    The panel contains a dcc.Graph component that will display the goodness-of-fit plot after running the fit.

    Parameters:
    -----------
    page_id: string, the id of the page to use for the goodness-of-fit plot

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Goodness of Fit tab. 
    The TabsTab will have the label "Goodness of Fit" and the TabsPanel will contain a dcc.Graph component with id {"type": "gof-plot", "page": page_id} 
    and default figure set to plotly_goodness_of_fit(). The TabsPanel will have styles set to make it flexible and responsive.
    """

    tabstab = dmc.TabsTab("Goodness of Fit", value="gof")
    panel = dmc.TabsPanel(value="gof", children=[
        dcc.Graph(
            id={"type": "gof-plot", "page": page_id},
            figure=plotly_goodness_of_fit(),
            style={'height': '100%'},
            config={'responsive': True},
        )
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel


def dist_stats_tab(page_id):
    """
    Creates the Distance Statistics tab panel for the fit results tabs. This will display a table of distance distribution statistics after running a fit.
    The panel contains a dmc.Table component that will display the distance distribution statistics after running the fit.  

    Parameters:
    -----------
    page_id: string, the id of the page to use for the distance statistics table

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Distance Statistics tab.
    The TabsTab will have the label "Dist. Stats" and the TabsPanel will contain a dmc.Table component with id {"type": "dist-stats-table", "page": page_id}
    and default data set to a table header with "Statistic", "Value", and "Confidence Interval (95%)". The TabsPanel will have styles set to make it flexible and responsive.

    """

    tabstab = dmc.TabsTab("Dist. Stats", value="dist-stats")

    panel =  dmc.TabsPanel(value="dist-stats", children=[
        dmc.Table(
            id={"type": "dist-stats-table", "page": page_id},
            data={
                "head": ["Statistic", "Value", "Confidence Interval (95%)"],
            },
            striped=True,
            highlightOnHover=True,
        )
    ], style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'})
    return tabstab, panel

def L_curve_tab(page_id):
    tabstab = dmc.TabsTab("L-Curve", value="l-curve")
    panel = dmc.TabsPanel(value="l-curve", children=[
        dcc.Graph(
            id={"type": "l-curve-plot", "page": page_id},
            figure=plotly_lcurve(),
            style={'height': '100%'},
            config={'responsive': True},
        )
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel

def dipolar_spectrum_tab(page_id):
    tabstab = dmc.TabsTab("Dipolar Spectrum", value="dip-spectrum")
    panel = dmc.TabsPanel(value="dip-spectrum", children=[
        dcc.Graph(
            id={"type": "dip-spectrum-plot", "page": page_id},
            figure=plotly_dipolar_spectrum(None),
            style={'height': '100%'},
            config={'responsive': True},
        )
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel

def fit_results_tabs(*tabs):
    """
    Creates a Mantine Paper component containing Tabs for the given tabs. Defaults value to the first tab provided.

    Parameters:
    *tabs: tuples of (dmc.TabsTab, dmc.TabsPanel) to include in the Tabs component
    
    returns:
    dmc.Paper containing the Tabs component with the specified tabs
    """
    tab_tabs = [tabs[i][0] for i in range(len(tabs))]
    tab_panels = [tabs[i][1] for i in range(len(tabs))]
    tab0_value = tabs[0][0].value if len(tabs) > 0 else None

    return dmc.Paper([
                    dmc.Tabs([
                        dmc.TabsList(tab_tabs),
                        *tab_panels
                        ], 
                    style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0}, value=tab0_value)
                    ], variant="outline",
                    style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0, 'overflow': 'hidden'})





def fit_plot(page_id, background_only=False):
    switch_style = {'display': 'none'} if background_only else None
    return dmc.Paper([
        dmc.Group([
            dmc.Text("Dataset:", size="md", id={"type": "fit-plot-dataset-label", "page": page_id}, mb=0),
            dmc.Switch(id={'type': 'fit-plot-showpathways','page':page_id},
                       onLabel="ON", offLabel="OFF",
                       label="Show Pathways", labelPosition='left',
                       size="lg",pr='lg',
                       style=switch_style),
        ],justify="space-between"),
        dcc.Graph(id={"type": "fit-plot", "page": page_id},
                figure=plotly_deerlab(None, background_only=background_only),
                style={'height': '100%'},
                config={'responsive': True})
                ],
                style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 300})

@callback(
    Output({'type': 'fit-results-store', 'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def plot_dataset(dataset_id):
    if not dataset_id:
        return None
    if not isinstance(dataset_id, list):
        dataset_id = [dataset_id]
    n_datasets = len(dataset_id)
    output = {"fit_type":None}
    
    if n_datasets == 1:
        session = get_session()
        dataset_entry = session.query(Dataset).filter_by(id=dataset_id[0]).first()
        dataset = dataarray_from_database_entry(dataset_entry)
        session.close()
        dataset = dataset.assign_coords(t=dataset.t.values)
        # Normalise the data:
        V = dataset.values.real
        V = V / np.max(V)
        output.update({'t': [dataset.t.values.tolist()], 'V': [V.tolist()]})
        return output
    elif n_datasets > 1:
        session = get_session()
        ts = []
        Vs = []
        for ds_id in dataset_id:
            dataset_entry = session.query(Dataset).filter_by(id=ds_id).first()
            dataset = dataarray_from_database_entry(dataset_entry)
            dataset = dataset.assign_coords(t=dataset.t.values)
            # Normalise the data:
            V = dataset.values.real
            V = V / np.max(V)
            ts.append(dataset.t.values.tolist())
            Vs.append(V.tolist())
        session.close()
        output.update({'t': ts, 'V': Vs})
        return output
    else:
        raise ValueError("Invalid dataset_id: expected a single ID or a list of IDs, got {}".format(dataset_id))

@callback(
    Output({"type": "fit-plot", "page": MATCH}, 'figure'),
    Output({'type': 'fit-plot-showpathways', 'page': MATCH}, 'disabled'),
    Input({'type': 'fit-plot-showpathways', 'page': MATCH}, 'checked'),
    Input({'type': 'fit-results-store', 'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def toggle_pathways(show_pathways, fit_dict):
    import dash
    outputs_list = dash.callback_context.outputs_list
    page_id = outputs_list[0]['id'].get('page') if outputs_list else None
    background_only = (page_id == 'background')

    if not fit_dict:
        return plotly_deerlab(None, background_only=background_only), True
    if 'data' not in fit_dict:
        return plotly_deerlab(fitresult=fit_dict, background_only=background_only), True
    fit = dl.json_loads(fit_dict['data'])
    if not hasattr(fit, 'pathways') or fit.pathways is None or len(fit.pathways) == 1:
        show_pathways = False
        pathway_option = False
    else:
        pathway_option = True
    return plotly_deerlab(fitresult=fit, showPathways=show_pathways or False, background_only=background_only), not pathway_option


def pathway_input(page_id):
    tooltip_msg = "Select which pathways to include in the fit. These will be applied to all datasets, if they are feasible for the corresponding experiment."
    return dmc.Tooltip(dmc.CheckboxGroup(
                id={'type': 'pathways-options', 'page': page_id},
                label="Pathways to include:",
                description="These pathways will be applied to all datasets, if they are fesiable for the corresponding experiment.",
                children=dmc.Group([
                    dmc.Checkbox(value='1', label='1'),
                    dmc.Checkbox(value='2', label='2'),
                    dmc.Checkbox(value='3', label='3'),
                    dmc.Checkbox(value='4', label='4'),
                    dmc.Checkbox(value='5', label='5'),
                ]),
                value=['1'], # Default selected pathways
            ),label=tooltip_msg, position="left", withArrow=True, transitionProps={"duration": 0},multiline=True,w="15%")

@callback(
    Output({"type": "fit-dl-modal",'page': MATCH}, "opened", allow_duplicate=True),
    Output({"type": "fit-dl-store",'page': MATCH}, "data", allow_duplicate=True),
    Input({"type":'download-fit-btn','page': MATCH}, 'n_clicks'),
    State({'type':'fit-results-store','page': MATCH}, 'data'),
    prevent_initial_call=True
)
def download_fit(n_clicks, fit_store):
    if n_clicks is None or not fit_store:
        return False, no_update
    
    return True, fit_store


# ---------------------------------------------------------------------------
# Overview Tab Components, Cards and Callbacks
# ---------------------------------------------------------------------------


METRIC_CONFIG = {
    "mnr":       {"title": "MNR",  "description": "Modulation Noise Ratio",           "thresholds": {"direction": "higher_better", "good": 50,   "moderate": 20}},
    "chi2":      {"title": "Chi²", "description": "Reduced Chi-squared",         "thresholds": {"direction": "lower_better",  "good": 1.5,  "moderate": 3}},
    "rmsd":      {"title": "RMSD", "description": "Root Mean Square Deviation",  "thresholds": {"direction": "lower_better",  "good": 0.01, "moderate": 0.02}},
    "lambda":    {"title": "λ",    "description": "Modulation Depth",            "thresholds": None},
    "mean_dist": {"title": "⟨r⟩",  "description": "Mean Distance (nm)",          "thresholds": None},
    "std_dist":  {"title": "σᵣ",   "description": "Std. Deviation (nm)",         "thresholds": None},
}


def _make_card_children(title, value, uncertainty=None, description=None, thresholds=None):
    """Builds the dmc.Stack children for an overview card. Used by overview_card and the update callback."""
    color = "gray"
    if value is not None and thresholds is not None:
        direction = thresholds.get("direction", "lower_better")
        good = thresholds.get("good")
        moderate = thresholds.get("moderate")
        if direction == "higher_better":
            color = "green" if value > good else "orange" if value > moderate else "red"
        else:
            color = "green" if value < good else "orange" if value < moderate else "red"

    value_str = "N/A" if value is None else f"{value:.4g}" if isinstance(value, float) else str(value)

    children = [
        dmc.Text(title, size="lg", fw=700),
        dmc.Text(value_str, size="xl", fw=700, c=color),
    ]
    if uncertainty is not None:
        unc_str = f"± {uncertainty:.4g}" if isinstance(uncertainty, float) else f"± {uncertainty}"
        children.append(dmc.Text(unc_str, size="sm", c="dimmed"))
    if description is not None:
        children.append(dmc.Text(description, size="xs", c="dimmed"))

    return dmc.Stack(children, gap=2, align="center")


def overview_card(metric_id, page_id, value=None, uncertainty=None):
    """
    Creates a rectangular card component for displaying a fit metric.

    Parameters:
    -----------
    metric_id: string key from METRIC_CONFIG (e.g. "mnr", "chi2")
    page_id: string, the id of the parent page — included in the component id for pattern-matching callbacks
    value: numeric or None; None renders "N/A"
    uncertainty: numeric or None; if provided shown as "± uncertainty"

    Returns:
    -----------
    dmc.Paper with id {"type": "overview-card", "metric": metric_id, "page": page_id}
    """
    config = METRIC_CONFIG.get(metric_id, {"title": metric_id, "description": None, "thresholds": None})
    return dmc.Paper(
        _make_card_children(config["title"], value, uncertainty, config["description"], config["thresholds"]),
        id={"type": "overview-card", "metric": metric_id, "page": page_id},
        withBorder=True,
        p="md",
        style={"textAlign": "center", "minWidth": 120},
    )





def overview_tab(page_id):
    """
    Creates an overview tab panel for the fit_results. This will display a number of key metrics about the fit in a simple format.
    The key metrics are displayed as a number of cards created by the function overview_card.
    The MNR, and chi2 and RMSD cards, change colour based on the value of the metric, with thresholds for good, moderate, and poor fit quality. 
    The thresholds are defined in the function overview_card.
    
    Displayed Cards:
    - MNR: Modulation Noise Ratio, with thresholds for good (>50), moderate (20-50), and poor (<20) fit quality
    - Chi2: reduced Chi-squared statistic, with thresholds for good (<1.5), moderate (1.5-3), and poor (>3) fit quality
    - RMSD: Root Mean Square Deviation, with thresholds for good (<0.05), moderate (0.05-0.1), and poor (>0.1) fit quality
    - Modulation Depth, lambda: no specific thresholds, just displays the value and uncertainty if available

    - The cards are arranged in a responsive grid layout that adjusts based on the screen size, with a gap between the cards.

        Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the overview tab.


    """
    tabstab = dmc.TabsTab("Overview", value="overview")
    panel = dmc.TabsPanel(value="overview", children=[
        # Dummy components so the shared overview-card callback can find all its MATCH inputs
        dcc.Store(id={"type": "fit-results-store-multi", "page": page_id}),
        html.Div(dmc.Pagination(id={"type": "fit-plot-pagination", "page": page_id}, total=1, value=1), style={"display": "none"}),
        *_overview_card_grids(page_id),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel


def overview_tab_global(page_id, n_datasets=1):
    """
    Creates an overview tab panel for globally fitted datasets, where each dataset's
    metrics are displayed on a separate page navigated by a dmc.Pagination component.
    The layout is identical to overview_tab but repeated over multiple pages.

    A dcc.Store with id {"type": "overview-global-data-store", "page": page_id} holds
    the metric data for all datasets as a list of dicts (one per dataset). A callback
    should update the cards when the pagination value changes.

    Parameters:
    -----------
    page_id: string, the id of the page
    n_datasets: int, the initial number of pages (datasets); defaults to 1

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the overview tab.
    """
    tabstab = dmc.TabsTab("Overview", value="overview")
    panel = dmc.TabsPanel(value="overview", children=[
        dcc.Store(id={"type": "overview-global-data-store", "page": page_id}, data=[]),
        dmc.Stack([
            *_overview_card_grids(page_id),
            dmc.Center(
                dmc.Pagination(
                    id={"type": "overview-pagination", "page": page_id},
                    total=n_datasets,
                    value=1,
                    withEdges=True,
                ),
                mb="md",
            ),
        ], gap="md")
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel


def _overview_card_grids(page_id):
    """Returns the two SimpleGrid rows of overview cards (shared between overview_tab and overview_tab_global)."""
    return [
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
        dmc.SimpleGrid(
            cols={"base": 1, "sm": 2},
            mb="md",
            spacing="md",
            children=[
                overview_card("mean_dist", page_id),
                overview_card("std_dist",  page_id),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Overview card callbacks — registered once, work for every page via MATCH
# ---------------------------------------------------------------------------

def _extract_overview_metrics(store_data,page_number=None):
    """
    Extracts overview card metrics from a fit-results-store dict.

    Reads from:
    - store_data['gof']        → MNR, chi2red (chi²), RMSD, lam (λ)
    - store_data['dist_stats'] → mean (⟨r⟩), std (σᵣ) with confidence intervals

    Returns a dict keyed by metric_id matching METRIC_CONFIG.
    """
    if not store_data:
        return {}

    if isinstance(store_data, list):
        store_data = store_data[page_number] if page_number is not None else store_data[0]

    gof = store_data.get('gof') or {}
    dist_stats = store_data.get('dist_stats') or {}
    if page_number is not None:
        if isinstance(gof, list):
            gof = gof[page_number] if page_number < len(gof) else {}
        if isinstance(dist_stats, list):
            dist_stats = dist_stats[page_number] if page_number < len(dist_stats) else {}

    def _gof(key, *aliases):
        for k in (key,) + aliases:
            v = gof.get(k)
            if v is not None:
                return float(v)
        return None

    def _dist(key):
        entry = dist_stats.get(key) or {}
        val = entry.get('value')
        ci = entry.get('ci')
        unc = (ci[1] - ci[0]) / 2 if ci else None
        return (float(val) if val is not None else None), (float(unc) if unc is not None else None)

    mean_val, mean_unc = _dist('mean')
    std_val, std_unc = _dist('std')

    return {
        'mnr':       {'value': _gof('MNR', 'mnr'),           'uncertainty': None},
        'chi2':      {'value': _gof('chi2red', 'chi2'),       'uncertainty': None},
        'rmsd':      {'value': _gof('RMSD', 'rmsd'),          'uncertainty': None},
        'lambda':    {'value': _gof('lam', 'lambda', 'LAM'),  'uncertainty': None},
        'mean_dist': {'value': mean_val,                       'uncertainty': mean_unc},
        'std_dist':  {'value': std_val,                        'uncertainty': std_unc},
    }


def _render_cards(outputs, metrics):
    """Renders card children for each output id using a metrics dict from _extract_overview_metrics."""
    result = []
    for out in outputs:
        metric = out["id"]["metric"]
        config = METRIC_CONFIG.get(metric, {"title": metric, "description": None, "thresholds": None})
        metric_data = metrics.get(metric, {})
        result.append(_make_card_children(
            title=config["title"],
            value=metric_data.get("value"),
            uncertainty=metric_data.get("uncertainty"),
            description=config["description"],
            thresholds=config["thresholds"],
        ))
    return result




@callback(
    Output({"type": "overview-card", "metric": ALL, "page": MATCH}, "children"),
    Input({"type": "fit-results-store", "page": MATCH}, "data"),
    Input({"type": "fit-results-store-multi", "page": MATCH}, "data"),
    Input({"type": "fit-plot-pagination", "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def update_overview_cards(store_data, store_data_multi, page_number=None):
    """Updates all overview cards on a page whenever fit-results-store changes."""
    import dash
    outputs = dash.callback_context.outputs_list
    if store_data_multi is not None:
        page_idx = (page_number or 1) - 1
        return _render_cards(outputs, _extract_overview_metrics(store_data_multi, page_idx))
    return _render_cards(outputs, _extract_overview_metrics(store_data))


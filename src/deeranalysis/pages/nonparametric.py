import json
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback
import dash_bootstrap_components as dbc
import numpy as np
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from autodeer import DEERanalysis
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, plotly_deerlab
dash.register_page(__name__)

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

page_id='non-parametric'


layout = html.Div([
    dmc.Title("Non-Parametric Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    
    dbc.Row([
        dbc.Col([
            create_dataset_modal(page_id=page_id),
            html.Div([
                dmc.Select(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                                id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            dmc.Space(h=10),     
            dmc.Select(
                label='Background Model',
                id='np-bg-model',
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),     
            dmc.CheckboxGroup(
                id='np-pathways-options',
                label="Pathways to include:",
                children=dmc.Group([
                    dmc.Checkbox(value='1', label='1'),
                    dmc.Checkbox(value='2', label='2'),
                    dmc.Checkbox(value='3', label='3'),
                    dmc.Checkbox(value='4', label='4'),
                    dmc.Checkbox(value='5', label='5'),
                ]),
                value=['1'], # Default selected pathways
            ),
            # Small vertical space
            dmc.Space(h=10),        
            dmc.Chip('Compactness', id='np-compactness-option', value=False, checked=False),
            dmc.Space(h=10),
            html.Label("Distance Axis:"),
            dcc.RangeSlider(
                id='np-distance-axis',
                min=1.5,
                max=12,
                step=0.25,
                value=[1.75, 6],
                marks={i: f'{i}' for i in range(1, 13)},
                allowCross=False,
                allow_direct_input=True,
                className="dmc"
                
                # tooltip={"placement": "bottom", "always_visible": True}
            ),
            dmc.Space(h=10),
            # dmc.Paper([
                dmc.Accordion(
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("Advanced Fit Options"),
                                dmc.AccordionPanel([
                                    dmc.Select(
                                        label='Regularization Method',
                                        description="Method for the automatic selection of the optimal regularization parameter:",
                                        id='np-regparam-method',
                                        data=regparam_options,
                                        value="bic"
                                    ),
                                    dmc.NumberInput(
                                        label="Fixed Regularization Parameter (α):",
                                        description="Set a fixed regularization parameter (overrides automatic selection)",
                                        id='np-alpha',
                                        type='text',
                                        value=None,
                                        step=0.001,
                                        allowNegative=False,
                                        className="mb-2"
                                    ),
                                    html.Label("Maximum Iterations:"),
                                    dcc.Input(
                                        id='np-max-iter',
                                        type='number',
                                        value=1000,
                                        className="form-control mb-2"
                                    ),
                                ])
                            ],
                            value="adv-options"
                        )
                    ]
                ),
            # ], withBorder=True, className="mb-3"),
            
            dmc.Space(h=10),
            
            dmc.Button("Run Fit", id="np-run-fit-btn", color="blue", className="mb-3"),
            dmc.Button("Save Fit", id="np-save-fit-btn", color="green", className="mb-3 ms-2", disabled=True),
            
            html.Div(id='np-fit-status')
        ], width=3),
        
        dbc.Col([
            dmc.Paper([
                dcc.Graph(id='np-fit-plot',
                        figure=plotly_deerlab(None))
                        ]),
            dmc.Paper([
                dmc.Tabs([dmc.TabsList([
                    dmc.TabsTab("Fit Results", value="FitResults"),
                    dmc.TabsTab("Goodness of Fit", value="gof"),
                    dmc.TabsTab("Dist. Stats", value="dist-stats")
                    ]),
                    dmc.TabsPanel(value="FitResults", children=[
                        dmc.CodeHighlight(id='fit-results-code',code=default_fit_results_code, language="python")]),
                    dmc.TabsPanel(value="gof", children=[dcc.Graph(id='np-gof-plot', figure=plotly_goodness_of_fit())]),
                    dmc.TabsPanel(value="dist-stats", children=[
                        dmc.Table(
                        id='dist-stats-table',
                        data={
                            "head": ["Statistic", "Value", "Confidence Interval (95%)"],
                        },
                        striped=True,
                        highlightOnHover=True,
                    )]),
                    ]),
                ], variant="outline"),
                    
        ], width=9)
    ]),
    
    # Hidden store for fit results
    dcc.Store(id='np-fit-results-store')
])
clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output("np-run-fit-btn", "loading", allow_duplicate=True),
        Input("np-run-fit-btn", "n_clicks"),
        prevent_initial_call=True,
    )

@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, 'data'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return options


@callback(
    Output('np-fit-results-store', 'data'),
    Output('np-fit-plot', 'figure',allow_duplicate=True),
    Output('np-run-fit-btn', 'loading', allow_duplicate=True),
    Output('fit-results-code', 'code', allow_duplicate=True),
    Output('np-gof-plot', 'figure', allow_duplicate=True),
    Output('dist-stats-table', 'data', allow_duplicate=True),
    Output('np-save-fit-btn', 'disabled'),

    Input('np-run-fit-btn', 'n_clicks'),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('np-bg-model', 'value'),
    State('np-compactness-option', 'checked'),
    State('np-distance-axis', 'value'),
    State('np-pathways-options', 'value'),
    State('np-regparam-method', 'value'),
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, bg_model_option,compactness,distance_axis,pathways_options,regparam_method):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass

    if not dataset_id:
        return dash.no_update
        
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    
    deadtime = dataset.attrs.get('deadtime', 0)/1e3
    dataset = dataset.assign_coords(t=dataset.t.values + float(deadtime))
    session.close()
    
    if triggered_id == {"page":page_id,"type":"dataset-dropdown"}:
        # Just plot the data
        t = dataset.t.values + float(deadtime)    
        V = dataset.values
        V = V / np.max(np.abs(V))

        fig = plotly_deerlab(fitresult=dataset)
        fig.update_layout(title=f"Dataset: {dataset_entry.name}", height=500, showlegend=True)
        dist_stats_output = {"head": ["Statistic", "Value", "Confidence Interval (95%)"]}
        return None, fig, False, default_fit_results_code, plotly_goodness_of_fit(),dist_stats_output, True
        
    if triggered_id == 'np-run-fit-btn':
        # Perform Fit using DeerLab
        
        # Distance vector
        r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range

        bg_model = getattr(dl, bg_model_option, dl.bg_hom3d)
        # Get pathways options from checklist
        pathways = [int(p) for p in pathways_options]
        print(f"Selected pathways: {pathways_options}")
        fit = DEERanalysis(dataset,
            compactness=compactness,
            model=None,
            ROI=False,
            bg_model=bg_model,
            r=r,
            pathways=pathways,
            regparam=regparam_method)


        # Create plots
        t = fit.t
        V = fit.Vexp
        r = fit.r

        fig = plotly_deerlab(fitresult=fit)
        fig.update_layout(title=f"Fit Result: {dataset_entry.name}", height=500, showlegend=True)

        gof_fig = plotly_goodness_of_fit(fit)

        dist_stats = dl.diststats(r,fit.P,fit.PUncert)
        dist_stats_output = {"head": ["Statistic", "Value", "Confidence Interval (95%)"],
                             "body": dists_stats_to_list(*dist_stats)}
        fit_dict = fit_to_dict(fit)
        return fit_dict, fig, False, fit.__str__(), gof_fig,dist_stats_output, False

    return dash.no_update

@callback(
    Output('np-fit-status', 'children'),
    Input('np-save-fit-btn', 'n_clicks'),
    State( {'type': 'dataset-dropdown', 'page': page_id},'value'),
    State('np-fit-results-store', 'data'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_id,dataset_store):
    if not dataset_store or not dataset_id:
        print(f"No fit results to save or no dataset selected.")
        return dash.no_update
        
    session = get_session()
    
    new_fit = Fit(
        dataset_id=dataset_id,
        name=f"NP Fit",
        **dataset_store
    )
    
    session.add(new_fit)
    session.commit()
    session.close()
    
    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)


def fit_to_dict(fit):
    """Takes a fit objects and converts it to a dictionary for storage in the database."""
    output = {}
    if isinstance(fit, dl.FitResult):
        output['engine'] = 'DeerLab'
    output['fit_type'] = 'non-parametric'
    output['dist_model'] = None
    output['bg_model'] = fit.Bmodel.name if fit.Bmodel else None
    output['t'] = fit.t.tolist() if fit.t is not None else None
    output['model'] = fit.model.tolist() if fit.model is not None else None
    output['P_model'] = fit.P.tolist() if fit.P is not None else None
    output['pathways'] = fit.pathways if hasattr(fit, 'pathways') else None
    output['r'] = fit.r.tolist() if fit.r is not None else None
    output['PUncert'] = None
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
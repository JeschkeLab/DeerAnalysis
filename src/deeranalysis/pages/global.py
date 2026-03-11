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
from deeranalysis.components.download_modal import create_fit_download_modal

from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, plotly_deerlab,dists_stats_to_list, fit_to_dict,name_dataset_from_dict
dash.register_page(__name__)

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

page_id='global'
layout = html.Div([
    dmc.Title("Global Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    
    
    dbc.Row([
        dbc.Col([
            dmc.Alert("Only a basic global fitting is implemented for full customisability please use the scripted version of DeerLab.", title="Note!", color="blue",withCloseButton=True),
            create_dataset_modal(page_id=page_id),
            create_fit_download_modal(page_id=page_id),
            html.Div([
                dmc.MultiSelect(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                                id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            dmc.Space(h=10),     
            dmc.Select(
                label='Background Model',
                id='gl-bg-model',
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),     
            dmc.CheckboxGroup(
                id='gl-pathways-options',
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
            dmc.Text("Adv. Options:", size="sm", fw=500, mb=4),        
            dmc.Chip('Compactness', id='gl-compactness-option', value=False, checked=False),
            dmc.Space(h=10),
            dmc.Text("Distance Axis:", size="sm", fw=500, mb=4),
            dcc.RangeSlider(
                id='gl-distance-axis',
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
            dmc.Text("Global Fitting:", size="sm", fw=500, mb=4),
            dmc.Group(dmc.ChipGroup([
                dmc.Chip('P(r)',value='pr', checked=False),
                dmc.Chip('Background',value='background', checked=False),
                dmc.Chip('Modulation Depth',value='mod-depth', checked=False),
            ],
            multiple=True,
            id='gl-global-fitting',
            value=['pr'],
            )),
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
                                        id='gl-regparam-method',
                                        data=regparam_options,
                                        value="bic"
                                    ),
                                    dmc.NumberInput(
                                        label="Fixed Regularization Parameter (α):",
                                        description="Set a fixed regularization parameter (overrides automatic selection)",
                                        id='gl-alpha',
                                        type='text',
                                        value=None,
                                        step=0.001,
                                        allowNegative=False,
                                        className="mb-2"
                                    ),
                                    html.Label("Maximum Iterations:"),
                                    dcc.Input(
                                        id='gl-max-iter',
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
            
            dmc.Button("Run Fit", id="gl-run-fit-btn", color="blue", className="mb-3"),
            dmc.Button("Save Fit", id="gl-save-fit-btn", color="green", className="mb-3 ms-2", disabled=True),
            
            html.Div(id='gl-fit-status')
        ], width=3),
        
        dbc.Col([
            dmc.Paper([
                dcc.Graph(id='gl-fit-plot',
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
                    dmc.TabsPanel(value="gof", children=[dcc.Graph(id='gl-gof-plot', figure=plotly_goodness_of_fit())]),
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
    dcc.Store(id='gl-fit-results-store')
])
clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output("gl-run-fit-btn", "loading", allow_duplicate=True),
        Input("gl-run-fit-btn", "n_clicks"),
        prevent_initial_call=True,
    )

@callback(
    Output('gl-global-fitting', 'value'),
    Input('gl-global-fitting', 'value'),
    State('gl-global-fitting', 'value'),
    prevent_initial_call=True
)
def ensure_one_selected(value, previous_value):
    if not value:
        return previous_value or ['pr']
    return value

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
    Output('gl-fit-results-store', 'data'),
    Output('gl-fit-plot', 'figure',allow_duplicate=True),
    Output('gl-run-fit-btn', 'loading', allow_duplicate=True),
    Output('fit-results-code', 'code', allow_duplicate=True),
    Output('gl-gof-plot', 'figure', allow_duplicate=True),
    Output('dist-stats-table', 'data', allow_duplicate=True),
    Output('gl-save-fit-btn', 'disabled'),
    Output("notification-container", "sendNotifications"),


    Input('gl-run-fit-btn', 'n_clicks'),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('gl-bg-model', 'value'),
    State('gl-compactness-option', 'checked'),
    State('gl-distance-axis', 'value'),
    State('gl-pathways-options', 'value'),
    State('gl-regparam-method', 'value'),
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, bg_model_option,compactness,distance_axis,pathways_options,regparam_method):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if dataset_id is None:
        return dash.no_update

    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass
    if triggered_id == 'np-run-fit-btn':
        if n_clicks < 1:
            return dash.no_update

        # check that more than 1 datasets are selected
        if not dataset_id or len(dataset_id) < 2:
            error_notification = [{
                "title": "Error",
                "message": "Please select at least 2 datasets for global fitting.",
                "color": "red",
                "autoClose": 3000,
                "icon": DashIconify(icon='mdi:alert-circle', width=20),
                "position":"top-center"
            }]
            return dash.no_update, dash.no_update, False, dash.no_update, dash.no_update, dash.no_update, True, error_notification
    
    # Get the datasets from the database
    session = get_session()
    datasets = []
    for dataset_id in dataset_id:
        dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset_entry is None:
            print(f"Dataset with id {dataset_id} not found in the database.")
        dataset = dataarray_from_database_entry(dataset_entry)
        
        deadtime = dataset.attrs.get('deadtime', 0)/1e3
        dataset = dataset.assign_coords(t=dataset.t.values + float(deadtime))
        datasets.append(dataset)
    session.close()
    return dash.no_update
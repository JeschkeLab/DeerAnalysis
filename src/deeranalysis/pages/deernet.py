import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure, dataarray_from_database_entry
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.components.dataset_search_model import create_dataset_modal
dash.register_page(__name__)


layout = html.Div([
    dmc.Title("DeerNet Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dbc.Row([
        dbc.Col([
            dmc.Alert("Only DeerNet 1 models are currently supported. DeerNet 2 is coming soon!", title="Warning!", color="yellow"),
            html.Label("Select Dataset"),
            create_dataset_modal(page_id='deernet'),
            dbc.Row([
            dbc.Col([dcc.Dropdown(id='dn-dataset-dropdown', placeholder="Select a dataset")]),
            dbc.Col([dmc.ActionIcon(DashIconify(icon='material-symbols:search',width=20),id='open-dataset-search-btn',size="lg", variant="default")], width='auto')
            ]),
            dmc.Select(label='Model Size',
                id='dn-model-size',
                data=[
                    {'value': '128', 'label': '128'},
                    {'value': '256', 'label': '256'},
                    {'value': '512', 'label': '512'},
                ],
                value='512',
                className="mb-3"
            ),
            dbc.Row([
            dbc.Col([dmc.Select(label='Uncertainty Type',
                id='dn-uncertainty-type',
                data=[
                    {'value': 'net', 'label': 'Network ensemble'},
                    {'value': 'boot', 'label': 'Bootstrap'},
                ],
                value='net',
                className="mb-3"
            )]),
            dbc.Col([dmc.NumberInput(
                label="Number of Bootstrap Samples",
                id="dn-bootstrap-samples",
                min=10,
                max=1000,
                step=10,
                value=100,
                className="mb-3",
                disabled=True
            )]),
            ]),

            html.Br(),
            
            dbc.Button("Run Fit", id="dn-run-fit-btn", color="primary", className="mb-3"),
            dbc.Button("Save Fit", id="dn-save-fit-btn", color="success", className="mb-3 ms-2", disabled=True),
            
            html.Div(id='dn-fit-status')
        ], width=3),
        
        dbc.Col([
            dcc.Graph(id='dn-fit-plot',
                      figure=create_subplot_figure('horizontal'))
        ], width=9)
    ]),
    
    # Hidden store for fit results
    dcc.Store(id='dn-fit-results-store')
])



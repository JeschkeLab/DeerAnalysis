import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import json
import numpy as np
import deerlab as dl
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure, dataarray_from_database_entry
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from autodeer import DEERanalysis
from deeranalysis.components.dataset_search_model import create_dataset_modal
dash.register_page(__name__)

layout = html.Div([
    html.H1("Non-Parametric Fit"),
    html.Hr(),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Dataset"),
            create_dataset_modal(),
            dbc.Row([
            dbc.Col([dcc.Dropdown(id='np-dataset-dropdown', placeholder="Select a dataset")]),
            dbc.Col([dmc.ActionIcon(DashIconify(icon='material-symbols:search',width=20),id='open-dataset-search-btn',size="lg", variant="default")], width='auto')
            ]),
            html.Br(),
            
            html.Label("Background Model"),
            dcc.Dropdown(
                id='np-bg-model',
                options=[
                    {'label': 'None', 'value': 'none'},
                    {'label': 'Homogeneous 3D', 'value': 'bg_hom3d'},
                    {'label': 'Exponential', 'value': 'bg_exp'}
                ],
                value='bg_hom3d'
            ),
            dbc.Row([
                dbc.Col([html.Label("Pathways:")]),
                dbc.Col([dcc.Checklist(
                    ['1', '2', '3', '4'],
                    ['1', '4'],
                    inline=True,
                    id='np-pathways-options',
                    labelStyle={'margin-right': '15px', 'margin-left': '5px'})])
            ]),
            dbc.Col([html.Label("Adv. Options:")]),
            dmc.Chip('Compactness', id='np-compactness-option', value=False, checked=False),
            html.Label("Distance Axis:"),
            dcc.RangeSlider(
                id='np-distance-axis',
                min=1.2,
                max=10,
                step=0.25,
                value=[1.5, 6],
                marks={i: f'{i}' for i in range(1, 12)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            html.Br(),
            
            dbc.Button("Run Fit", id="np-run-fit-btn", color="primary", className="mb-3"),
            dbc.Button("Save Fit", id="np-save-fit-btn", color="success", className="mb-3 ms-2", disabled=True),
            
            html.Div(id='np-fit-status')
        ], width=3),
        
        dbc.Col([
            dcc.Graph(id='np-fit-plot',
                      figure=create_subplot_figure('horizontal'))
        ], width=9)
    ]),
    
    # Hidden store for fit results
    dcc.Store(id='np-fit-results-store')
])

@callback(
    Output('np-dataset-dropdown', 'options'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': ds.id} for ds in datasets]
    session.close()
    return options

@callback(
    Output("dataset-search-modal", "opened",allow_duplicate=True),
    Input("open-dataset-search-btn", "n_clicks"),
    prevent_initial_call=True
)
def open_search_modal(n_clicks):
    if n_clicks:
        return True
    return False

@callback(
    Output("dataset-search-modal", "opened",allow_duplicate=True),
    Output("np-dataset-dropdown", "value"),
    Input("select-dataset-btn", "n_clicks"),
    State("dataset_table", "selectedRows"),
    prevent_initial_call=True
)
def select_dataset_from_modal(n_clicks, selected_rows):
    if n_clicks and selected_rows:
        dataset_title = selected_rows[0].get('Title')
        session = get_session()
        dataset = session.query(Dataset).filter_by(name=dataset_title).first()
        session.close()
        return False, dataset.id
    return dash.no_update, dash.no_update

@callback(
    Output('np-fit-plot', 'figure',allow_duplicate=True),
    Input('np-dataset-dropdown', 'value'),
    State('np-fit-plot', 'figure'),
    prevent_initial_call=True
)
def new_dataset_selected(dataset_id,current_fig):
    if not dataset_id:
        return dash.no_update
        
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    session.close()
    # Extract delays
    delays = dataset_entry.delays if dataset_entry.delays else {}

    deadtime = dataset.attrs.get('deadtime', 0)/1e3
    # Plot data
    t = dataset.t.values + float(deadtime)
    V = dataset.values
    V = V / np.max(np.abs(V))
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Time Domain", "Distance Domain"))
    fig.add_trace(go.Scatter(x=t, y=V.real, mode='lines', name='Data (Re)', marker=dict(size=5, color='black')), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=V.imag, mode='lines', name='Data (Im)', marker=dict(size=5, color='gray')), row=1, col=1)
    fig.update_layout(title=f"Dataset: {dataset.name}", xaxis_title="Time", yaxis_title="Signal")
    return fig

@callback(
    Output('np-fit-plot', 'figure',allow_duplicate=True),
    # Output('np-fit-results-store', 'data'),
    # Output('np-save-fit-btn', 'disabled'),
    Input('np-run-fit-btn', 'n_clicks'),
    Input('np-dataset-dropdown', 'value'),
    State('np-bg-model', 'value'),
    State('np-compactness-option', 'checked'),
    State('np-distance-axis', 'value'),
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, bg_model_name,compactness,distance_axis):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if not dataset_id:
        return dash.no_update
        
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    
    deadtime = dataset.attrs.get('deadtime', 0)/1e3
    
    session.close()
    
    if triggered_id == 'np-dataset-dropdown':
        # Just plot the data
        t = dataset.t.values + float(deadtime)    
        V = dataset.values
        V = V / np.max(np.abs(V))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=V, mode='lines', name='Data'))
        fig.update_layout(title=f"Dataset: {dataset_entry.name}", xaxis_title="Time", yaxis_title="Signal")
        return fig.to_dict()
        
    if triggered_id == 'np-run-fit-btn':
        # Perform Fit using DeerLab
        
        # Distance vector
        dataset = dataarray_from_database_entry(dataset_entry)
        dataset = dataset.assign_coords(t=dataset.t.values + float(deadtime))
        r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range
        # compactness = False # Default
        bg_model_name = dl.bg_hom3d
        pathways = [1]
        fit = DEERanalysis(dataset,
            compactness=compactness,
            model=None,
            ROI=False,
            bg_model=bg_model_name,
            r=r,
            pathways=pathways)


        # Create plots
        t = fit.t
        V = fit.Vexp
        r = fit.r
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Time Domain", "Distance Domain"))

        fig.add_trace(go.Scatter(x=t, y=V.real, mode='markers', name='Data (Re)', marker=dict(size=3, color='black')), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=fit.model.real, mode='lines', name='Fit (Re)', line=dict(color='red')), row=1, col=1)
        
        Pfit = fit.P
        # Distance domain
        fig.add_trace(go.Scatter(x=r, y=Pfit, mode='lines', name='P(r)', line=dict(color='blue')), row=1, col=2)
        # fig.add_trace(go.Scatter(x=r, y=results['Pci95_upper'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=2)
        # fig.add_trace(go.Scatter(x=r, y=results['Pci95_lower'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 0, 255, 0.2)', name='95% CI'), row=1, col=2)
        
        fig.update_layout(title=f"Fit Result: {dataset_entry.name}", height=500, showlegend=True)

        
        return fig

    return dash.no_update

@callback(
    Output('np-fit-status', 'children'),
    Input('np-save-fit-btn', 'n_clicks'),
    State('np-fit-results-store', 'data'),
    State('np-dataset-dropdown', 'value'),
    State('np-bg-model', 'value'),
    prevent_initial_call=True
)
def save_fit(n_clicks, results, dataset_id, bg_model):
    if not results or not dataset_id:
        return dash.no_update
        
    session = get_session()
    
    new_fit = Fit(
        dataset_id=dataset_id,
        name=f"NP Fit - {bg_model}",
        fit_type='non-parametric',
        model_description={'bg_model': bg_model},
        parameters={}, # Non-parametric doesn't have simple parameters for P
        fit_results=json.dumps(results)
    )
    
    session.add(new_fit)
    session.commit()
    session.close()
    
    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)

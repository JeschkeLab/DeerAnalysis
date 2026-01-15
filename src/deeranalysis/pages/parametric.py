import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import json
import numpy as np
import deerlab as dl
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure


dash.register_page(__name__)

layout = html.Div([
    html.H1("Parametric Fit"),
    html.Hr(),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Dataset"),
            dcc.Dropdown(id='p-dataset-dropdown', placeholder="Select a dataset"),
            html.Br(),
            
            html.Label("Distance Model"),
            dcc.Dropdown(
                id='p-dist-model',
                options=[
                    {'label': '1 Gaussian', 'value': 'dd_gauss'},
                    {'label': '2 Gaussians', 'value': 'dd_gauss2'},
                    {'label': 'Rice', 'value': 'dd_rice'}
                ],
                value='dd_gauss'
            ),
            html.Br(),
            
            html.Label("Background Model"),
            dcc.Dropdown(
                id='p-bg-model',
                options=[
                    {'label': 'None', 'value': 'none'},
                    {'label': 'Homogeneous 3D', 'value': 'bg_hom3d'},
                    {'label': 'Exponential', 'value': 'bg_exp'}
                ],
                value='bg_hom3d'
            ),
            html.Br(),
            
            dbc.Button("Run Fit", id="p-run-fit-btn", color="primary", className="mb-3"),
            dbc.Button("Save Fit", id="p-save-fit-btn", color="success", className="mb-3 ms-2", disabled=True),
            
            html.Div(id='p-fit-status')
        ], width=3),
        
        dbc.Col([
            dcc.Graph(id='p-fit-plot',
                      figure=create_subplot_figure('horizontal'))
        ], width=9)
    ]),
    
    dcc.Store(id='p-fit-results-store')
])

@callback(
    Output('p-dataset-dropdown', 'options'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': ds.id} for ds in datasets]
    session.close()
    return options

@callback(
    Output('p-fit-plot', 'figure'),
    Output('p-fit-results-store', 'data'),
    Output('p-save-fit-btn', 'disabled'),
    Input('p-run-fit-btn', 'n_clicks'),
    Input('p-dataset-dropdown', 'value'),
    State('p-dist-model', 'value'),
    State('p-bg-model', 'value'),
    prevent_initial_call=True
)
def run_fit(n_clicks, dataset_id, dist_model_name, bg_model_name):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if not dataset_id:
        return go.Figure(), None, True
        
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    
    t = np.array(json.loads(dataset.data_t))
    V = np.array(json.loads(dataset.data_V))
    session.close()
    
    if triggered_id == 'p-dataset-dropdown':
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=V, mode='lines', name='Data'))
        fig.update_layout(title=f"Dataset: {dataset.name}", xaxis_title="Time", yaxis_title="Signal")
        return fig, None, True
        
    if triggered_id == 'p-run-fit-btn':
        r = np.linspace(1.5, 6, 100)
        
        # Select models
        if dist_model_name == 'dd_gauss':
            Pmodel = dl.dd_gauss
        elif dist_model_name == 'dd_gauss2':
            Pmodel = dl.dd_gauss2
        elif dist_model_name == 'dd_rice':
            Pmodel = dl.dd_rice
            
        if bg_model_name == 'none':
            Bmodel = None
        elif bg_model_name == 'bg_hom3d':
            Bmodel = dl.bg_hom3d
        elif bg_model_name == 'bg_exp':
            Bmodel = dl.bg_exp
            
        # Construct model
        Vmodel = dl.dipolarmodel(t, r, Pmodel=Pmodel, Bmodel=Bmodel)
        
        # Fit
        fit = dl.fit(Vmodel, V)
        
        Vfit = fit.model
        Pfit = fit.P
        Pci95 = fit.Puncert.ci(95)
        
        # Extract parameters
        # fit.param is a dictionary of parameter names and values? No, fit object has attributes for parameters.
        # Or fit.modelparam?
        # DeerLab fit object has a __getattr__ that delegates to the result.
        # We can get parameters from fit.modelparam or similar?
        # Actually fit object *is* the result object (FitResult).
        # It has attributes for each parameter.
        # We can iterate over model parameters.
        
        param_dict = {p: getattr(fit, p) for p in Vmodel._parameter_list()}
        # Convert numpy types to python types for JSON
        param_dict = {k: float(v) if isinstance(v, (np.float64, np.float32)) else v for k, v in param_dict.items()}

        results = {
            't': t.tolist(),
            'V': V.tolist(),
            'r': r.tolist(),
            'Vfit': Vfit.tolist(),
            'Pfit': Pfit.tolist(),
            'Pci95_lower': Pci95[:,0].tolist(),
            'Pci95_upper': Pci95[:,1].tolist(),
            'parameters': param_dict,
            'stats': {k: v for k, v in fit.stats.items() if isinstance(v, (int, float, str))}
        }
        
        # Create plots
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Time Domain", "Distance Domain"))
        
        fig.add_trace(go.Scatter(x=t, y=V, mode='markers', name='Data', marker=dict(size=3, color='black')), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=Vfit, mode='lines', name='Fit', line=dict(color='red')), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=r, y=Pfit, mode='lines', name='P(r)', line=dict(color='blue')), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=results['Pci95_upper'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=results['Pci95_lower'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 0, 255, 0.2)', name='95% CI'), row=1, col=2)
        
        fig.update_layout(height=500)
        
        return fig, results, False

    return go.Figure(), None, True

@callback(
    Output('p-fit-status', 'children'),
    Input('p-save-fit-btn', 'n_clicks'),
    State('p-fit-results-store', 'data'),
    State('p-dataset-dropdown', 'value'),
    State('p-dist-model', 'value'),
    State('p-bg-model', 'value'),
    prevent_initial_call=True
)
def save_fit(n_clicks, results, dataset_id, dist_model, bg_model):
    if not results or not dataset_id:
        return dash.no_update
        
    session = get_session()
    
    new_fit = Fit(
        dataset_id=dataset_id,
        name=f"Parametric Fit - {dist_model} + {bg_model}",
        fit_type='parametric',
        model_description={'dist_model': dist_model, 'bg_model': bg_model},
        parameters=json.dumps(results['parameters']),
        fit_results=json.dumps(results)
    )
    
    session.add(new_fit)
    session.commit()
    session.close()
    
    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)

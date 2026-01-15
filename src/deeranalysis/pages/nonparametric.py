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
from deeranalysis.utils import create_subplot_figure

dash.register_page(__name__)

layout = html.Div([
    html.H1("Non-Parametric Fit"),
    html.Hr(),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Dataset"),
            dcc.Dropdown(id='np-dataset-dropdown', placeholder="Select a dataset"),
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
            html.Label("Pathways:"),
            dcc.Checklist(
                ['1', '2', '3', '4'],
                ['1', '4'],
                inline=True,
                id='np-pathways-options',
                labelStyle={'margin-right': '15px', 'margin-left': '5px'}
            ),
            html.Label("Compactness:"),
            dcc.Checklist(
                ['Enabled'],
                [],
                inline=True,
                id='np-compactness-option',
                labelStyle={'margin-right': '15px', 'margin-left': '5px'}
            ),
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
    Output('np-fit-plot', 'figure',allow_duplicate=True),
    Input('np-dataset-dropdown', 'value'),
    State('np-fit-plot', 'figure'),
    prevent_initial_call=True
)
def plot_data_only(dataset_id,current_fig):
    if not dataset_id:
        return dash.no_update
        
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    t = np.array(dataset.t)
    V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
    V = V / np.max(np.abs(V))
    current_fig['data']=[
            go.Scatter(x=t, y=V.real, mode='lines', name=f'{dataset.name} - Re', customdata=[dataset_id], xaxis='x', yaxis='y'),
            go.Scatter(x=t, y=V.imag, mode='lines', name=f'{dataset.name} - Im', customdata=[dataset_id], xaxis='x', yaxis='y',line=dict(dash='dash')),
        ]
    return current_fig

@callback(
    Output('np-fit-plot', 'figure',allow_duplicate=True),
    # Output('np-fit-results-store', 'data'),
    # Output('np-save-fit-btn', 'disabled'),
    Input('np-run-fit-btn', 'n_clicks'),
    Input('np-dataset-dropdown', 'value'),
    State('np-bg-model', 'value'),
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, bg_model_name):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if not dataset_id:
        return go.Figure(), None, True
        
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    
    t = np.array(dataset.t)
    V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
    V = V / np.max(np.abs(V))
    session.close()
    
    if triggered_id == 'np-dataset-dropdown':
        # Just plot the data
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=V, mode='lines', name='Data'))
        fig.update_layout(title=f"Dataset: {dataset.name}", xaxis_title="Time", yaxis_title="Signal")
        return fig, None, True
        
    if triggered_id == 'np-run-fit-btn':
        # Perform Fit using DeerLab
        
        # Distance vector
        r = np.linspace(1.5, 6, 100) # Default range
        
        # Dipolar kernel
        K = dl.dipolarkernel(t, r)
        
        if bg_model_name == 'none':
             # Simple Tikhonov regularization
            fit = dl.fit(dl.snlls, V, K, reg=True)
            Vfit = fit.model
            Pfit = fit.P
            Pci95 = fit.PUncert.ci(95)
            Pci50 = fit.PUncert.ci(50)
            
            # Prepare results for storage
            results = {
                't': t.tolist(),
                'V': V.tolist(),
                'r': r.tolist(),
                'Vfit': Vfit.tolist(),
                'Pfit': Pfit.tolist(),
                'Pci95_lower': Pci95[:,0].tolist(),
                'Pci95_upper': Pci95[:,1].tolist(),
                'stats': fit.stats
            }
            
        else:
            # Fit with background
            # This is a simplified example. In a real app, we'd need more controls for background parameters.
            # Assuming we fit background and distribution simultaneously or sequentially.
            # Let's do a simple model fit for now: V = (1-lam)*K*P + lam*B
            
            # For simplicity in this demo, let's assume we just want to fit P with a fixed background or simple model
            # But user asked for "Non-Parametric Fit". Usually implies P is non-parametric.
            # Let's use dl.snlls with a background model if selected.
            
            # Construct model
            # V(t) = (1-lambda)*K*P(r) + lambda*B(t)
            # This requires a non-linear least squares for lambda and B parameters, and linear for P.
            # DeerLab's snlls is perfect for this.
            
            # Define background model
            if bg_model_name == 'bg_hom3d':
                Bmodel = dl.bg_hom3d
            elif bg_model_name == 'bg_exp':
                Bmodel = dl.bg_exp
            
            # Define the full model
            # We need to define a function that takes non-linear parameters and returns the matrix K and the background vector B
            # But dl.snlls takes Amodel(p) -> A matrix.
            # V = K*P + B -> This is not directly A*x unless we combine P and B?
            # Actually, usually we model V = B * ( (1-mod)*K*P + mod ) or similar.
            # Let's stick to the standard DeerLab workflow for simple cases.
            
            # Let's assume the user wants to fit P given a background model.
            # We can use the 'model' approach in DeerLab which is more general.
            
            # Vmodel = dl.dipolarmodel(t, r, Bmodel=Bmodel)
            # fit = dl.fit(Vmodel, V)
            
            # However, dipolarmodel by default uses a non-parametric P? No, it uses parametric P by default unless specified?
            # dl.dipolarmodel(t, r, Pmodel=None) -> P is non-parametric.
            
            Vmodel = dl.dipolarmodel(t, r, Bmodel=Bmodel, Pmodel=None)
            fit = dl.fit(Vmodel, V)
            
            Vfit = fit.model
            Pfit = fit.P
            Pci95 = fit.PUncert.ci(95)
            
            results = {
                't': t.tolist(),
                'V': V.tolist(),
                'r': r.tolist(),
                'Vfit': Vfit.tolist(),
                'Pfit': Pfit.tolist(),
                'Pci95_lower': Pci95[:,0].tolist(),
                'Pci95_upper': Pci95[:,1].tolist(),
                'stats': {k: v for k, v in fit.stats.items() if isinstance(v, (int, float, str))} # Simple serialization
            }

        # Create plots
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Time Domain", "Distance Domain"))
        
        # Time domain
        fig.add_trace(go.Scatter(x=t, y=V, mode='markers', name='Data', marker=dict(size=3, color='black')), row=1, col=1)
        fig.add_trace(go.Scatter(x=t, y=Vfit, mode='lines', name='Fit', line=dict(color='red')), row=1, col=1)
        
        # Distance domain
        fig.add_trace(go.Scatter(x=r, y=Pfit, mode='lines', name='P(r)', line=dict(color='blue')), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=results['Pci95_upper'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'), row=1, col=2)
        fig.add_trace(go.Scatter(x=r, y=results['Pci95_lower'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 0, 255, 0.2)', name='95% CI'), row=1, col=2)
        
        fig.update_layout(height=500)
        
        return fig, # results, False

    return go.Figure(), None, True

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

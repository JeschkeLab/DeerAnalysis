import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import json
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit

dash.register_page(__name__)

layout = html.Div([
    html.H1("Comparison"),
    html.Hr(),
    
    dbc.Row([
        dbc.Col([
            html.Label("Select Dataset"),
            dcc.Dropdown(id='comp-dataset-dropdown', placeholder="Select a dataset"),
            html.Br(),
            
            html.Label("Select Fits to Compare"),
            dcc.Checklist(
                id='comp-fits-checklist',
                options=[],
                value=[],
                labelStyle={'display': 'block'}
            ),
        ], width=3),
        
        dbc.Col([
            dcc.Graph(id='comp-plot')
        ], width=9)
    ])
])

@callback(
    Output('comp-dataset-dropdown', 'options'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': ds.id} for ds in datasets]
    session.close()
    return options

@callback(
    Output('comp-fits-checklist', 'options'),
    Output('comp-fits-checklist', 'value'),
    Input('comp-dataset-dropdown', 'value')
)
def update_fits_checklist(dataset_id):
    if not dataset_id:
        return [], []
        
    session = get_session()
    fits = session.query(Fit).filter_by(dataset_id=dataset_id).all()
    options = [{'label': f"{f.name} (ID: {f.id})", 'value': f.id} for f in fits]
    session.close()
    
    return options, []

@callback(
    Output('comp-plot', 'figure'),
    Input('comp-dataset-dropdown', 'value'),
    Input('comp-fits-checklist', 'value')
)
def update_comparison_plot(dataset_id, selected_fit_ids):
    if not dataset_id:
        return go.Figure()
        
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    
    t = np.array(json.loads(dataset.data_t))
    V = np.array(json.loads(dataset.data_V))
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Time Domain", "Distance Domain"))
    
    # Plot Data
    fig.add_trace(go.Scatter(x=t, y=V, mode='markers', name='Data', marker=dict(size=3, color='black')), row=1, col=1)
    
    if selected_fit_ids:
        for fit_id in selected_fit_ids:
            fit = session.query(Fit).filter_by(id=fit_id).first()
            if fit and fit.fit_results:
                results = json.loads(fit.fit_results)
                
                Vfit = np.array(results['Vfit'])
                Pfit = np.array(results['Pfit'])
                r = np.array(results['r'])
                
                fig.add_trace(go.Scatter(x=t, y=Vfit, mode='lines', name=f"{fit.name} - Fit"), row=1, col=1)
                fig.add_trace(go.Scatter(x=r, y=Pfit, mode='lines', name=f"{fit.name} - P(r)"), row=1, col=2)
                
    session.close()
    
    fig.update_layout(height=500)
    return fig

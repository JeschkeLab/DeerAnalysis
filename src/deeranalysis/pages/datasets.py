import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import json
from deeranalysis.utils.database import get_session, Dataset
import numpy as np
import dash_ag_grid as dag  
import plotly.graph_objs as go
from deeranalysis.utils import create_subplot_figure


dash.register_page(__name__, path='/')
columnDefs = [
    {'field': 'Title',
     'filter': 'agTextColumnFilter',
},
    {'field': 'Project',
     'filter': 'agTextColumnFilter',
},
    {'field': 'Sample',
     'filter': 'agTextColumnFilter',
},
    {'field': 'Experiment',
     'filter': 'agTextColumnFilter',
},
    {'field': '# Fits'},
    {'field': 'SNR'},
    {
        "field": "Compare",
        "cellRenderer": "DMC_Button",
        "cellRendererParams": {
            "variant": "outline",
            "leftIcon": "ph:eye",
            "color": "green",
            "radius": "xl"
        },
    },
    {
        "field": "Fit",
        "cellRenderer": "DMC_Button",
        "cellRendererParams": {
            "variant": "outline",
            "leftIcon": "material-symbols:model-training",
            "color": "orange",
            "radius": "xl"
        },
    },
]
layout = html.Div([
    html.H1("Datasets"),
    html.Hr(),
    
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([html.H4("Existing Datasets")], width="auto"),
                dbc.Col([dbc.Button("Refresh", id="refresh-datasets-btn", color="primary", size="sm", n_clicks=0)], width="auto"),
            ], className="align-items-center g-2 mb-2"),
            
            # Wrapper for the first grid: flex-grow-1 ensures it fills available space
            # minHeight-0 is crucial for allowing it to shrink when the bottom grid appears
            html.Div(
                dag.AgGrid(
                    id="datasets_table",
                    columnDefs=columnDefs,
                    defaultColDef={"sortable": True, "resizable": True},
                    rowData=[],
                    className="ag-theme-alpine",
                    columnSize="sizeToFit",
                    style={"height": "100%", "width": "100%"},
                ),
                style={"flex": "1", "minHeight": "0", "width": "100%"}
            ),

            dbc.Button(
                "List fits for selected dataset",
                id="collapse-button",
                className="my-2",
                color="primary",
                size="sm",
                n_clicks=0,
            ),
            
            dbc.Collapse(
                # Fixed height container for the second grid
                # This ensures consistent size and forces the top grid to shrink via flexbox
                html.Div(
                    dag.AgGrid(
                        id="datasets_details_table",
                        columnDefs=columnDefs,
                        defaultColDef={"sortable": True, "resizable": True},
                        rowData=[],
                        className="ag-theme-alpine",
                        columnSize="sizeToFit",
                        style={"height": "100%", "width": "100%"},
                    ),
                    style={"height": "35vh"}
                ),
                id="collapse-content",
                is_open=False,
            ),
        # Adjusted height calculation to account for header (typically ~120px) and footer (e.g. ~60px)
        ], width=8, style={"display": "flex", "flexDirection": "column", "height": "calc(100vh - 180px)", "overflow": "hidden"}),
        
        dbc.Col([
            dcc.Graph(
                id="datasets-graph",
                figure=create_subplot_figure(),
                style={"height": "700px"}
            ),
        ], width=4),
    ], style={"flex": "1", "overflow": "hidden"}),
], style={"height": "calc(100vh - 60px)", "display": "flex", "flexDirection": "column", "overflow": "hidden"})



@callback(
    Output("datasets_table", "rowData"),
    Input("refresh-datasets-btn", "n_clicks")
)
def update_datasets_table(n_clicks):
    if n_clicks is None:
        return dash.no_update
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()
    
    data = []
    for ds in datasets:
        data.append({
            'Title': ds.name,
            'Project': ds.project,
            'Sample': ds.sample,
            'Experiment': ds.exp,
            '# Fits': ds.n_fits,
            'Fit': 'Fit',
            'Compare': 'Compare',
        })
    
    return data

@callback(
    Output("collapse-content", "is_open"),
    Input("collapse-button", "n_clicks"),
    State("collapse-content", "is_open"),
)
def toggle_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@callback(
    Output("datasets-graph", "figure"),
    Input("datasets_table", "cellRendererData"),
    State("datasets-graph", "figure")
)
def add_dataset_to_comparison(cellRendererData,current_fig):
    # Toggle dataset in comparison view when clicked from table
    if cellRendererData is None:
        return dash.no_update
    if cellRendererData.get('colId') != 'Compare':
        return dash.no_update
    row = cellRendererData['rowIndex']

    # Get dataset info from database
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()
    
    dataset = datasets[row]
    dataset_id = dataset.id
    
    # Get current figure or create new one
    
    # if current_fig is None or not current_fig.get('data'):
    #     # No existing data, add the dataset
    #     t = np.array(dataset.t)
    #     V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
    #     V = V / np.max(np.abs(V))
        
    #     return {
    #         'data': [
    #             go.Scatter(x=t, y=V.real, mode='lines', name=f'{dataset.name} - Re', customdata=[dataset_id]),
    #             go.Scatter(x=t, y=V.imag, mode='lines', name=f'{dataset.name} - Im', customdata=[dataset_id]),
    #         ],
    #         'layout': go.Layout(
    #             xaxis_title='Time (us)',
    #             yaxis_title='Signal (a.u.)',
    #             template='plotly_white'
    #         )
    #     }
    
    # Check if dataset is already in the figure
    if not current_fig.get('data'):
        current_fig['data'] = []
    existing_traces = current_fig['data']
    dataset_exists = any(trace.get('customdata', [None])[0] == dataset_id for trace in existing_traces)
    
    if dataset_exists:
        # Remove dataset traces
        new_traces = [trace for trace in existing_traces if trace.get('customdata', [None])[0] != dataset_id]
    else:
        # Add dataset traces
        t = np.array(dataset.t)
        V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
        V = V / np.max(np.abs(V))
        
        # Add real part
        new_traces = existing_traces + [
            go.Scatter(x=t, y=V.real, mode='lines', name=f'{dataset.name}', customdata=[dataset_id], xaxis='x', yaxis='y'),
        ]
        # Add imag part
        new_traces += [
            go.Scatter(x=t, y=V.imag, mode='lines', customdata=[dataset_id], xaxis='x', yaxis='y', line=dict(dash='dash', color=new_traces[-1]['line']['color'] if new_traces else None))
            ]
    
    current_fig['data'] = new_traces
    return current_fig

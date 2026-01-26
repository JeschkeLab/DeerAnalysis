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
from sqlalchemy.orm import Session


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
                    dashGridOptions={"rowSelection": "single"},
                ),
                style={"flex": "1", "minHeight": "0", "width": "100%", "overflow": "auto"}
            ),

            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "List fits for selected dataset",
                        id="collapse-button",
                        color="primary",
                        size="sm",
                        n_clicks=0,
                    ),
                ], width="auto"),
                dbc.Col([
                    dbc.Button(
                        "Show metadata and delays",
                        id="metadata-button",
                        color="secondary",
                        size="sm",
                        n_clicks=0,
                    ),
                ], width="auto"),
            ], className="my-2 g-2"),
            
            dbc.Collapse(
                html.Div(id="collapse-content-container"),
                id="collapse-content",
                is_open=False,
            ),
        # Adjusted height calculation to account for header (typically ~120px) and footer (e.g. ~60px)
        ], width=8, style={"display": "flex", "flexDirection": "column", "height": "calc(100vh - 220px)", "overflow": "hidden"}),
        
        dbc.Col([
            dcc.Graph(
                id="datasets-graph",
                figure=create_subplot_figure(),
                style={"height": "700px"}
            ),
        ], width=4),
    ], style={"flex": "1", "overflow": "hidden"}),
], style={"height": "calc(100vh - 100px)", "display": "flex", "flexDirection": "column", "overflow": "hidden"})



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
    [Output("collapse-content", "is_open"),
     Output("collapse-content-container", "children")],
    [Input("collapse-button", "n_clicks"),
     Input("metadata-button", "n_clicks")],
    [State("collapse-content", "is_open"),
     State("datasets_table", "selectedRows")],
)
def toggle_collapse_sections(fits_clicks, metadata_clicks, is_open, selected_rows):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return False, html.Div()
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # If clicking the same button that's already open, close it
    if button_id == "collapse-button":
        if is_open and ctx.triggered[0].get('value', 0) > 0:
            # Check if we need to toggle
            content = html.Div(
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
            )
            return not is_open if dash.callback_context.triggered[0]['value'] > 0 else is_open, content
        else:
            content = html.Div(
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
            )
            return True, content
    
    elif button_id == "metadata-button":
        # Get metadata content
        if not selected_rows:
            metadata_content = html.P("No dataset selected", className="text-muted")
            delays_content = html.P("No dataset selected", className="text-muted")
        else:
            selected_row = selected_rows[0]
            dataset_title = selected_row.get('Title')
            
            session = get_session()
            dataset = session.query(Dataset).filter_by(name=dataset_title).first()
            
            if not dataset:
                session.close()
                metadata_content = html.P("Dataset not found", className="text-muted")
                delays_content = html.P("Dataset not found", className="text-muted")
            else:
                # Parse metadata
                metadata_items = []
                if dataset.meta:
                    try:
                        for key, value in dataset.meta.items():
                            metadata_items.append(
                                dbc.Row([
                                    dbc.Col(html.Strong(f"{key}:"), width=4),
                                    dbc.Col(str(value), width=8),
                                ], className="mb-1")
                            )
                    except:
                        metadata_items = [html.P("Unable to parse metadata")]
                else:
                    metadata_items = [html.P("No metadata available", className="text-muted")]
                
                metadata_content = html.Div(metadata_items)
                
                # Parse delays
                if dataset.delays:
                    delays_content = []
                    try:
                        for key, value in dataset.delays.items():
                            delays_content.append(
                                dbc.Row([
                                    dbc.Col(html.Strong(f"{key}:"), width=4),
                                    dbc.Col(str(value), width=8),
                                ], className="mb-1")
                            )
                    except:
                        delays_content = html.P("Unable to parse delays")
                else:
                    delays_content = html.P("No delays available", className="text-muted")
                
                session.close()
        
        content = html.Div([
            html.H5("Metadata", className="mt-2"),
            html.Div(metadata_content, className="mb-3"),
            html.H5("Delays"),
            html.Div(delays_content),
        ], style={"maxHeight": "30vh", "overflow": "auto", "padding": "10px", "border": "1px solid #dee2e6", "borderRadius": "5px"})
        
        return True, content
    
    return is_open, html.Div()

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
        deadtime = float(dataset.meta.get('deadtime', 0))/1e3
        t = np.array(dataset.t) + deadtime
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



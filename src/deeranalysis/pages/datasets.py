import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset
from dash_iconify import DashIconify

import numpy as np
import dash_ag_grid as dag
import plotly.graph_objs as go
from deeranalysis.utils import create_subplot_figure,dataarray_from_database_entry
from deeranalysis.utils.deerlab_options import plotly_deerlab
from deeranalysis.components.download_modal import create_dataset_download_modal, create_fit_download_modal
from deeranalysis.components.metadata_table import build_metadata_section,metadata_long_values_model

import json
dash.register_page(__name__, path='/')
page_id = "datasets-page"

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
    {'field': '# Fits',"width": 120,},
    {'field': 'SNR'},
    {
        "field": "Open",
        "headerName": "",
        "cellRenderer": "DMC_DualIconButton",
        "cellRendererParams": {
            "leftIcon": "mdi:open-in-new",
            "rightIcon": "mdi:download-outline",
            "color": "blue",
            "size": "sm",
            "radius": "sm",
        },
        "width": 80,
        "suppressSizeToFit": True,
        "sortable": False,
        "filter": False,
    },
]
fits_columnDefs = [
    {'field': 'Fit Name', 'filter': 'agTextColumnFilter'},
    {'field': 'Engine', 'filter': 'agTextColumnFilter', 'width': 100},
    {'field': 'Type', 'filter': 'agTextColumnFilter', 'width': 150},
    {'field': 'Pathways', 'filter': 'agTextColumnFilter',"width": 120,},
    {'field': 'RMSD',"width": 120,},
    {
        "field": "Open",
        "headerName": "",
        "cellRenderer": "DMC_DualIconButton",
        "cellRendererParams": {
            "leftIcon": "mdi:open-in-new",
            "rightIcon": "mdi:download-outline",
            "color": "blue",
            "size": "sm",
            "radius": "sm",
        },
        "width": 80,
        "suppressSizeToFit": True,
        "sortable": False,
        "filter": False,
    },
]

layout = html.Div([
    dmc.Title("Datasets", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dcc.Location(id="datasets-redirect", refresh=True),
    dcc.Store(id="metadata-modal-store", data=""),
    create_dataset_download_modal(page_id = page_id),
    create_fit_download_modal(page_id = page_id),
    metadata_long_values_model(page_id),

    dbc.Row([
        dbc.Col([
            # dbc.Row([
            #     dbc.Col([html.H4("Existing Datasets")], width="auto"),
            #     dbc.Col([dbc.Button("Refresh", id="refresh-datasets-btn", color="primary", size="sm", n_clicks=0)], width="auto"),
            # ], className="align-items-center g-2 mb-2"),
            dmc.Group([dmc.Title("Existing Datasets", order=3),
                       dmc.ActionIcon(DashIconify(icon="mdi:refresh", width=18), id="refresh-datasets-btn", variant="outline", color="blue",n_clicks=0)], mb="md"),
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
                    dmc.Button(
                        "Show details for selected dataset",
                        id="collapse-button",
                        # color="primary",
                        # size="sm",
                        # n_clicks=0,
                    ),
                ], width="auto"),
            ], className="my-2 g-2"),

            dbc.Collapse(
                id="collapse-content",
                is_open=False,
                children=dmc.Tabs(
                    id="details-tabs",
                    value="fits",
                    children=[
                        dmc.TabsList([
                            dmc.TabsTab("Fits", value="fits"),
                            dmc.TabsTab("Metadata & Delays", value="metadata"),
                        ]),
                        dmc.TabsPanel(
                            value="fits",
                            children=html.Div(
                                dag.AgGrid(
                                    id="datasets_details_table",
                                    columnDefs=fits_columnDefs,
                                    defaultColDef={"sortable": True, "resizable": True},
                                    rowData=[],
                                    className="ag-theme-alpine",
                                    columnSize="sizeToFit",
                                    style={"height": "28vh", "width": "100%"},
                                ),
                            ),
                        ),
                        dmc.TabsPanel(
                            value="metadata",
                            children=html.Div(
                                id="metadata-content",
                                style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                            ),
                        ),
                    ],
                ),
                style={"height": "35vh"},
            ),

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
            'SNR': '',
            'Open': '',
            'id': ds.id,
        })
    
    return data

@callback(
    Output("collapse-content", "is_open"),
    Input("collapse-button", "n_clicks"),
    State("collapse-content", "is_open"),
    prevent_initial_call=True,
)
def toggle_collapse(n_clicks, is_open):
    return not is_open


@callback(
    Output("datasets_details_table", "rowData"),
    Output("metadata-content", "children"),
    Output("metadata-modal-store", "data"),
    Input("datasets_table", "selectedRows"),
    prevent_initial_call=True,
)
def populate_details(selected_rows):
    if not selected_rows:
        return [], html.P("No dataset selected.", className="text-muted"), {}

    dataset_title = selected_rows[0].get('Title')
    dataset_id = selected_rows[0].get('id')
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()

    if not dataset:
        session.close()
        return [], html.P("Dataset not found.", className="text-muted"), {}

    # --- Fits tab ---
    fits_data = []
    if dataset.fits:
        for fit in dataset.fits:
            fits_data.append({
                'Fit Name': getattr(fit, 'name', ''),
                'Engine': getattr(fit, 'engine', ''),
                'Type': getattr(fit, 'fit_type', ''),
                'Pathways': getattr(fit, 'pathways', ''),
                'RMSD': getattr(fit, 'rmsd', ''),
                'Date': str(getattr(fit, 'date', '')),
                'id': fit.id,
            })

    # --- Metadata tab ---
    metadata_children, long_values_store = build_metadata_section(dataset)

    session.close()
    return (
        fits_data,
        metadata_children,
        long_values_store,
    )


@callback(
    Output({"type": "metadata-value-modal",'page': page_id}, "opened"),
    Output({"type":"metadata-value-modal-text",'page': page_id}, "value"),
    Input({"type": "metadata-show-btn", "key": dash.ALL}, "n_clicks"),
    State("metadata-modal-store", "data"),
    prevent_initial_call=True,
)
def open_metadata_modal(n_clicks_list, store_data):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n for n in (n_clicks_list or []) if n):
        return dash.no_update, dash.no_update

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    key = json.loads(triggered_id)["key"]
    full_value = (store_data or {}).get(key, "Value not found.")
    return True, full_value


@callback(
    Output("datasets-graph", "figure"),
    Input("datasets_table", "selectedRows"),
    prevent_initial_call=True,
)
def update_graph_on_selection(selected_rows):
    """Automatically show the selected dataset in the comparison graph."""
    if not selected_rows:
        return create_subplot_figure()

    row = selected_rows[0]
    dataset_id = row.get('id')

    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    
    deadtime = dataset.attrs.get('deadtime', 0)/1e3
    dataset = dataset.assign_coords(t=dataset.t.values + float(deadtime))
    session.close()

    if dataset is None:
        return plotly_deerlab(None, orientation='v')


    fig = plotly_deerlab(dataset,orientation='v')
    
    return fig


@callback(
    Output("datasets-redirect", "pathname"),
    Output({"type": "dataset-dl-modal",'page': page_id}, "opened"),
    Output({"type": "dataset-dl-store",'page': page_id}, "data"),
    Input("datasets_table", "cellRendererData"),
    State("datasets_table","rowData"),
    prevent_initial_call=True,
)
def dataset_buttons(cellRendererData,rowData):
    """Navigate to the dataset detail page when the Open button is clicked."""
    if cellRendererData is None or cellRendererData.get('colId') != 'Open':
        return dash.no_update
    action = (cellRendererData.get('value') or {}).get('action')
    rowIndex = cellRendererData.get('rowIndex', None)
    selected_row = rowData[rowIndex] if rowIndex is not None and rowIndex < len(rowData) else None
    ds_id = selected_row.get('id') if selected_row else None
    if ds_id is None:
        return dash.no_update
    if action != 'left':  # only "open" navigates; "download" can be handled separately
        return dash.no_update, True, ds_id

    return f'/dataset/{ds_id}', dash.no_update, dash.no_update

@callback(
    Output("datasets-redirect", "pathname",allow_duplicate=True),
    Output({"type": "fit-dl-modal",'page': page_id}, "opened"),
    Output({"type": "fit-dl-store",'page': page_id}, "data"),
    Input("datasets_details_table", "cellRendererData"),
    State("datasets_details_table","rowData"),
    prevent_initial_call=True,
)
def fit_buttons(cellRendererData,rowData):
    """Navigate to the dataset detail page when the Open button is clicked."""
    if cellRendererData is None or cellRendererData.get('colId') != 'Open':
        return dash.no_update
    action = (cellRendererData.get('value') or {}).get('action')
    rowIndex = cellRendererData.get('rowIndex', None)
    selected_row = rowData[rowIndex] if rowIndex is not None and rowIndex < len(rowData) else None
    ds_id = selected_row.get('id') if selected_row else None
    if ds_id is None:
        return dash.no_update
    if action != 'left':  # only "open" navigates; "download" can be handled separately
        return dash.no_update, True, ds_id

    return f'/fits/{ds_id}', dash.no_update, dash.no_update
def update_fit_table():
    # This function can be called after adding/removing fits to update the fit table in the collapse section
    pass

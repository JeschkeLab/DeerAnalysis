import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset
import numpy as np
import dash_ag_grid as dag
import plotly.graph_objs as go
from deeranalysis.utils import create_subplot_figure
import json
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
fits_columnDefs = [
    {'field': 'Fit Name', 'filter': 'agTextColumnFilter'},
    {'field': 'Method', 'filter': 'agTextColumnFilter'},
    {'field': 'RMSD'},
    {'field': 'Date'},
]

layout = html.Div([
    dmc.Title("Datasets", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dcc.Store(id="metadata-modal-store", data=""),

    # Modal for long metadata values — must be inside layout
    dmc.Modal(
        id="metadata-value-modal",
        title="Full Value",
        children=[
            # dmc.ScrollArea(
            #     h="45%",
                # children=
                dmc.Textarea(
                    id="metadata-value-modal-text",
                    value="",
                    readOnly=True,
                    autosize=True,
                    style={"width": "100%", "fontFamily": "monospace"},
                ),
            # )
        ],
        size="70%",
        opened=False,
    ),

    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col([html.H4("Existing Datasets")], width="auto"),
                dbc.Col([dbc.Button("Refresh", id="refresh-datasets-btn", color="primary", size="sm", n_clicks=0)], width="auto"),
            ], className="align-items-center g-2 mb-2"),

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
                        "Show details for selected dataset",
                        id="collapse-button",
                        color="primary",
                        size="sm",
                        n_clicks=0,
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
            'Fit': 'Fit',
            'Compare': 'Compare',
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
    session = get_session()
    dataset = session.query(Dataset).filter_by(name=dataset_title).first()

    if not dataset:
        session.close()
        return [], html.P("Dataset not found.", className="text-muted"), {}

    # --- Fits tab ---
    fits_data = []
    if dataset.fits:
        for fit in dataset.fits:
            fits_data.append({
                'Fit Name': getattr(fit, 'name', ''),
                'Method': getattr(fit, 'method', ''),
                'RMSD': getattr(fit, 'rmsd', ''),
                'Date': str(getattr(fit, 'date', '')),
            })

    # --- Metadata tab ---
    MAX_LEN = 80 # Max length before truncation in the table
    long_values_store = {}  # key -> full string, for the modal store

    def make_value_cell(key, value):
        val_str = str(value)
        if len(val_str) > MAX_LEN:
            long_values_store[key] = val_str
            return html.Td([
                html.Span(
                    val_str[:MAX_LEN] + "…",
                    style={"marginRight": "8px", "fontFamily": "monospace"},
                ),
                dmc.Button(
                    "Show",
                    id={"type": "metadata-show-btn", "key": key},
                    size="compact-xs",
                    variant="subtle",
                    n_clicks=0,
                ),
            ])
        return html.Td(val_str, style={"fontFamily": "monospace"})

    def build_table_rows(items_dict):
        rows = []
        for key, value in items_dict.items():
            rows.append(html.Tr([
                html.Td(html.Strong(str(key)), style={"whiteSpace": "nowrap", "paddingRight": "16px"}),
                make_value_cell(key, value),
            ]))
        return rows

    metadata_sections = []

    if dataset.meta:
        try:
            rows = build_table_rows(dataset.meta)
            metadata_sections.append(dmc.Title("Metadata", order=5, mb="xs"))
            metadata_sections.append(
                dmc.Table(
                    children=[html.Tbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                    mb="md",
                )
            )
        except Exception:
            metadata_sections.append(html.P("Unable to parse metadata."))
    else:
        metadata_sections.append(html.P("No metadata available.", className="text-muted"))

    if dataset.delays:
        try:
            rows = build_table_rows(dataset.delays)
            metadata_sections.append(dmc.Divider(my="sm"))
            metadata_sections.append(dmc.Title("Delays", order=5, mb="xs"))
            metadata_sections.append(
                dmc.Table(
                    children=[html.Tbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                )
            )
        except Exception:
            metadata_sections.append(html.P("Unable to parse delays."))
    else:
        metadata_sections.append(html.P("No delays available.", className="text-muted"))

    session.close()
    return (
        fits_data,
        html.Div(metadata_sections, style={"padding": "8px"}),
        long_values_store,
    )


@callback(
    Output("metadata-value-modal", "opened"),
    Output("metadata-value-modal-text", "value"),
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
    Input("datasets_table", "cellRendererData"),
    State("datasets-graph", "figure")
)
def add_dataset_to_comparison(cellRendererData, current_fig):
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

def update_fit_table():
    # This function can be called after adding/removing fits to update the fit table in the collapse section
    pass

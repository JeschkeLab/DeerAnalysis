"""
Dataset detail page — shows all information about a single dataset in an editable format.
Accessible at /dataset/<dataset_id>.
"""
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_ag_grid as dag
from dash_iconify import DashIconify
import plotly.graph_objs as go
import numpy as np
import json

from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils import create_subplot_figure
from deeranalysis.components.metadata_table import build_metadata_section,build_delays_table, metadata_long_values_model

dash.register_page(__name__, path_template="/dataset/<dataset_id>")
page_id = "dataset-detail"
# ---------------------------------------------------------------------------
# Column definitions for the fits sub-table
# ---------------------------------------------------------------------------
fits_columnDefs = [
    {"field": "Name",   "filter": "agTextColumnFilter", "flex": 2},
    {"field": "Type",   "filter": "agTextColumnFilter", "flex": 1},
    {"field": "Engine", "filter": "agTextColumnFilter", "flex": 1},
    {"field": "RMSD",   "flex": 1},
    {"field": "Date",   "flex": 2},
]

# ---------------------------------------------------------------------------
# Layout (function — receives path parameter)
# ---------------------------------------------------------------------------
def layout(dataset_id=None):
    if dataset_id is None:
        return _error_page("No dataset ID provided.")

    try:
        session = get_session()
        if session is None:
            return _error_page("Database is not available.")
        dataset = session.query(Dataset).filter_by(id=int(dataset_id)).first()
        session.close()
    except Exception as exc:
        return _error_page(f"Error loading dataset: {exc}")

    if dataset is None:
        return _error_page(f"Dataset with ID {dataset_id} was not found.")

    # ---- prepare data -------------------------------------------------------
    fits_rows = _build_fits_rows(dataset)
    meta_str   = json.dumps(dataset.meta,   indent=2) if dataset.meta   else "{}"
    delays_str = json.dumps(dataset.delays, indent=2) if dataset.delays else "{}"
    created_str = str(dataset.created_at) if dataset.created_at else ""

    metadata_children, long_values_store = build_metadata_section(dataset,delays=False)  # Pre-build metadata section to populate long_values_store for modals
    delays_children = build_delays_table(dataset) if dataset.delays else html.P("No delays available.", className="text-muted")
    # ---- time-domain signal preview ----------------------------------------
    signal_fig = _build_signal_figure(dataset)

    # ---- layout -------------------------------------------------------------
    return html.Div([
        dcc.Store(id="dd-dataset-id", data=int(dataset_id)),
        metadata_long_values_model(page_id),
        dcc.Store(id={"type":"metadata-modal-store","page":page_id}, data=long_values_store),  # Store for long metadata values for modals
        dmc.Modal(
            id="dd-delete-modal",
            title="Confirm Deletion",
            children=[
                html.P("Are you sure you want to delete this dataset and all associated fits? This action cannot be undone."),
                dmc.Group([
                    dmc.Button("Cancel", id="dd-cancel-delete-btn"),
                    dmc.Button("Delete", id="dd-confirm-delete-btn", color="red"),
                ], justify="flex-end", mt="md"),
            ],
            centered=True,
        ),

        # ---- header ---------------------------------------------------------
        dmc.Group([
            dmc.Anchor(
                dmc.ActionIcon(
                    DashIconify(icon="mdi:arrow-left", width=20),
                    variant="subtle",
                    size="lg",
                    # title="Back to Datasets",
                ),
                href="/",
                underline=False,
            ),
            dmc.Title(dataset.name, order=1),
            dmc.Space(style={"flex": 1}),
            dmc.Button(
                "Download",
                id="dd-download-btn",
                color="blue",
                leftSection=DashIconify(icon="mdi:download", width=18),
            ),
            dmc.ActionIcon(
                DashIconify(icon="mdi:trash", width=18),
                variant="outline",
                color="red",
                id="dd-delete-btn",
            ),
        ], mb="md", align="center"),

        dmc.Divider(mb="lg"),

        # ---- notification area ----------------------------------------------
        html.Div(id="dd-notification"),

        dbc.Row([
            # ---- left column: editable fields -------------------------------
            dbc.Col([

                # Basic info
                dmc.Paper([
                    dmc.Group([
                        dmc.Title("Basic Information", order=4, mb="sm"),
                        dmc.Space(style={"flex": 1}),
                        dmc.ActionIcon(DashIconify(icon='mdi:edit',),id='dd-basic-info-editable',variant="subtle",)],),
                    dmc.Grid([
                        dmc.GridCol(
                            dmc.TextInput(id="dd-name", label="Name", value=dataset.name or "", disabled=True),
                            span=6,
                        ),
                        dmc.GridCol(
                            dmc.TextInput(id="dd-project", label="Project", value=dataset.project or "",disabled=True),
                            span=6,
                        ),
                        dmc.GridCol(
                            dmc.TextInput(id="dd-sample", label="Sample", value=dataset.sample or "",disabled=True),
                            span=6,
                        ),
                        dmc.GridCol(
                            dmc.Select(
                                id="dd-exp",
                                label="Experiment",
                                value=dataset.exp or "Unknown",
                                data=["4pDEER", "5pDEER", "3pDEER", "RIDME", "Unknown"],
                                allowDeselect=False,
                                disabled=True,
                            ),
                            span=6,
                        ),
                        dmc.GridCol(
                            dmc.TextInput(
                                id="dd-created",
                                label="Created At",
                                value=created_str,
                                disabled=True,
                            ),
                            span=6,
                        ),
                    ]),
                ], p="md", mb="md", withBorder=True, radius="md"),
                # Delays
                dmc.Paper([
                    dmc.Group([
                        dmc.Title("Delays", order=4, mb="sm"),
                        dmc.Space(style={"flex": 1}),
                        dmc.ActionIcon(DashIconify(icon='mdi:edit',),id='dd-delays-editable',variant="subtle",)],),
                    html.Div(
                        delays_children,
                        id="metadata-content",
                        style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                    ),
                ], p="md", mb="md", withBorder=True, radius="md"),

                # Metadata
                dmc.Paper([
                    dmc.Title("Metadata", order=4, mb="sm"),
                    # dmc.Textarea(
                    #     id="dd-metadata",
                    #     value=meta_str,
                    #     autosize=True,
                    #     minRows=4,
                    #     maxRows=16,
                    #     style={"fontFamily": "monospace", "width": "100%"},
                    # ),
                    html.Div(
                        metadata_children,
                        id="metadata-content",
                        style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                    ),
                ], p="md", mb="md", withBorder=True, radius="md"),

                

            ], md=6),

            # ---- right column: signal + fits --------------------------------
            dbc.Col([

                # Signal plot
                dmc.Paper([
                    dmc.Title("Signal Preview", order=4, mb="sm"),
                    dcc.Graph(
                        id="dd-signal-graph",
                        figure=signal_fig,
                        style={"height": "340px"},
                        config={"displayModeBar": False},
                    ),
                ], p="md", mb="md", withBorder=True, radius="md"),

                # Fits table
                dmc.Paper([
                    dmc.Title("Fits", order=4, mb="sm"),
                    dag.AgGrid(
                        id="dd-fits-table",
                        columnDefs=fits_columnDefs,
                        defaultColDef={"sortable": True, "resizable": True},
                        rowData=fits_rows,
                        className="ag-theme-alpine",
                        columnSize="sizeToFit",
                        style={"height": "220px", "width": "100%"},
                    ),
                ], p="md", mb="md", withBorder=True, radius="md"),

            ], md=6),
        ]),
    ], style={"padding": "20px"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_page(message: str):
    return html.Div([
        dmc.Group([
            dmc.Anchor(
                dmc.ActionIcon(
                    DashIconify(icon="mdi:arrow-left", width=20),
                    variant="subtle",
                    size="lg",
                ),
                href="/",
                underline=False,
            ),
            dmc.Title("Dataset Not Found", order=2),
        ], mb="md"),
        dmc.Alert(message, color="red", title="Error"),
    ], style={"padding": "20px"})


def _build_fits_rows(dataset):
    rows = []
    for fit in (dataset.fits or []):
        rmsd = ""
        if fit.gof and isinstance(fit.gof, dict):
            rmsd_val = fit.gof.get("rmsd", fit.gof.get("RMSD", ""))
            rmsd = f"{rmsd_val:.4f}" if isinstance(rmsd_val, float) else str(rmsd_val)
        rows.append({
            "Name":   getattr(fit, "name",       ""),
            "Type":   getattr(fit, "fit_type",   ""),
            "Engine": getattr(fit, "engine",     ""),
            "RMSD":   rmsd,
            "Date":   str(getattr(fit, "created_at", "")),
        })
    return rows


def _build_signal_figure(dataset):
    try:
        deadtime = float((dataset.meta or {}).get("deadtime", 0)) / 1e3
        t = np.array(dataset.t) + deadtime
        V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
        V = V / np.max(np.abs(V))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=V.real, mode="lines", name="Real"))
        fig.add_trace(go.Scatter(x=t, y=V.imag, mode="lines", name="Imag",
                                 line=dict(dash="dash")))
        fig.update_layout(
            xaxis_title="Time (µs)",
            yaxis_title="Signal (a.u.)",
            margin=dict(l=50, r=20, t=20, b=40),
            legend=dict(orientation="h", y=-0.2),
            height=300,
        )
        return fig
    except Exception:
        return go.Figure()


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def _alert(message: str, color: str, title: str):
    return dmc.Alert(
        message,
        color=color,
        title=title,
        withCloseButton=True,
        mb="md",
    )


@callback(
    Output("dd-delete-modal", "opened"),
    [Input("dd-delete-btn", "n_clicks"), Input("dd-cancel-delete-btn", "n_clicks")],
    prevent_initial_call=True,
)
def toggle_delete_modal(n_delete, n_cancel):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id == "dd-delete-btn":
        return True
    else:
        return False
    
@callback(
    Output("dd-notification", "children",allow_duplicate=True),
    Output("dd-delete-modal", "opened",allow_duplicate=True),
    Input("dd-confirm-delete-btn", "n_clicks"),
    State("dd-dataset-id", "data"),
    prevent_initial_call=True,
)
def delete_dataset(n_clicks,dataset_id):
    try:
        session = get_session()
        dataset = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset is None:
            session.close()
            return _alert("Dataset not found in the database.", "red", "Delete Error")

        session.delete(dataset)
        session.commit()
        session.close()
        return dcc.Location(pathname="/", id="dd-redirect-home"), False
    except Exception as exc:
        return _alert(f"Error deleting dataset: {exc}", "red", "Delete Error"), False
    

@callback(
    Output("dd-name", "disabled"),
    Output("dd-project", "disabled"),
    Output("dd-sample", "disabled"),
    Output("dd-exp", "disabled"),
    Output("dd-basic-info-editable", "children"),
    Input("dd-basic-info-editable", "n_clicks"),
    prevent_initial_call=True,
)
def make_basic_info_editable_save(n_clicks):
    # Toggle disabled state of basic info fields
    disabled = n_clicks % 2 == 0  # Even clicks -> disabled, Odd clicks -> enabled
    if disabled:
        button_icon = DashIconify(icon='mdi:edit',)
    else:
        button_icon = DashIconify(icon='mdi:content-save',)
    return disabled, disabled, disabled, disabled, button_icon

@callback(
        Output("dd-notification", "children",allow_duplicate=True),
        Input("dd-basic-info-editable", "n_clicks"),
        State("dd-dataset-id", "data"),
        State("dd-name", "value"),
        State("dd-project", "value"),
        State("dd-sample", "value"),
        State("dd-exp", "value"),
        prevent_initial_call=True,
)
def save_basic_info(n_clicks, dataset_id, name, project, sample, exp):
    if n_clicks % 2 != 0:
        # If button is in "Edit" mode, do not save
        return dash.no_update
    try:
        session = get_session()
        dataset = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset is None:
            session.close()
            return _alert("Dataset not found in the database.", "red", "Save Error")

        dataset.name    = name    or dataset.name
        dataset.project = project or ""
        dataset.sample  = sample  or ""
        dataset.exp     = exp     or dataset.exp

        session.commit()
        session.close()
        return _alert("Basic information saved successfully.", "green", "Saved")
    except Exception as exc:
        return _alert(f"Error saving basic information: {exc}", "red", "Save Error")
    

@callback(
    Output("dd-delays", "disabled"),
    Output("dd-delays-editable", "children"),
    Input("dd-delays-editable", "n_clicks"),
    prevent_initial_call=True,
)
def make_delays_editable_save(n_clicks):
    # Toggle disabled state of delays textarea
    disabled = n_clicks % 2 == 0  # Even clicks -> disabled, Odd clicks -> enabled
    if disabled:
        button_icon = DashIconify(icon='mdi:edit',)
    else:
        button_icon = DashIconify(icon='mdi:content-save',)
    return disabled, button_icon


@callback(
    Output({"type": "metadata-value-modal",'page': page_id}, "opened"),
    Output({"type": "metadata-value-modal-text",'page': page_id}, "value"),
    Input({"type": "metadata-show-btn", "key": dash.ALL}, "n_clicks"),
    State({"type": "metadata-modal-store",'page': page_id}, "data"),
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

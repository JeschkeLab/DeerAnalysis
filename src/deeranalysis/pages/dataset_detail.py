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
import datetime as dt
from deeranalysis.utils.database import get_session, Dataset,check_delays
from deeranalysis.utils import create_subplot_figure
from deeranalysis.components.metadata_table import build_metadata_section,build_delays_table, metadata_long_values_model,build_delays_AGgrid,delays_columnDefs
from deeranalysis.components.download_modal import create_fit_download_modal, create_dataset_download_modal

from deeranalysis.components.data_viewer import plot_upload,data_viewer_layout
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
    delays_children = build_delays_AGgrid(dataset,page_id,False) if dataset.delays else html.P("No delays available.", className="text-muted")
    tmin = np.min(dataset.t)*1e3 if dataset.t else 0

    # Convert stored boolean mask → list of masked indices for the store
    if dataset.mask and len(dataset.mask) == len(dataset.t):
        initial_masked = [i for i, keep in enumerate(dataset.mask) if not keep]
    else:
        initial_masked = []

    # ---- time-domain signal preview ----------------------------------------
    t_arr = np.array(dataset.t)
    initial_store = {
        'RealData': dataset.V,
        'ImagData': dataset.V_im,
        't': (t_arr - t_arr[0]).tolist(),  # zero-based µs
        'tmin': float(np.min(t_arr)),       # µs (matches the ns UI value / 1e3)
        'masked_indices': initial_masked,
    }

    signal_fig = plot_upload(initial_store, correct_phase=False, masking_enabled=True)

    # ---- layout -------------------------------------------------------------
    return html.Div([
        dcc.Store(id="dd-dataset-id", data=int(dataset_id)),
        dcc.Store(id={'type': 'dataset-store', 'page': page_id}, data=initial_store),
        metadata_long_values_model(page_id),
        create_dataset_download_modal(page_id=page_id),
        create_fit_download_modal(page_id=page_id),
        dcc.Location(id="dd-redirect", refresh=True),
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
                            dmc.DateTimePicker(
                                id="dd-created_at",
                                label="Created At",
                                value=dataset.created_at or "",
                                readOnly=True,
                                variant="default",
                                valueFormat = "YYYY-MM-DD HH:mm:ss",
                                # styles={"input": {"backgroundColor": "#fff", "color": "#212529", "opacity": 1, "cursor": "default"}},
                            ),
                            span=6,
                        ),
                        dmc.GridCol(
                            dmc.DateTimePicker(
                                id="dd-measured_at",
                                label="Measured At",
                                value=dataset.measured_at or "",
                                readOnly=True,
                                variant="default",
                                valueFormat = "YYYY-MM-DD HH:mm:ss",
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
                        [dmc.Group(dmc.NumberInput(tmin,allowNegative=True,label='tmin (ns):',id={"type": "tmin", 'page': page_id},disabled=True),align='center'),
                         dmc.Space(h=10),  
                         delays_children],
                        id="delays-content",
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
                    data_viewer_layout(page_id, title="Signal Preview", correct_phase=False, masking_enabled=True, inital_figure=signal_fig),
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
            "Date":   str(getattr(fit, "created_at", "")),
            "id":     fit.id,
            "RMSD":   rmsd,
        })
    return rows


def _build_signal_figure(dataset, tmin=0, masked_indices=None):
    try:
        t = np.array(dataset.t)
        t = t - t[0] + (tmin / 1e3)
        V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
        V = V / np.max(np.abs(V))
        masked = np.array(masked_indices or [], dtype=int)

        fig = go.Figure()
        # Invisible markers on Real so box/lasso selection captures points
        fig.add_trace(go.Scatter(
            x=t, y=V.real,
            mode="lines+markers",
            name="Real",
            marker=dict(size=8, opacity=0),
        ))
        fig.add_trace(go.Scatter(
            x=t, y=V.imag,
            mode="lines",
            name="Imag",
            line=dict(dash="dash"),
        ))
        if len(masked) > 0:
            fig.add_trace(go.Scatter(
                x=t[masked], y=V.real[masked],
                mode="markers", name="Masked (Real)",
                marker=dict(size=8, color="rgba(180,180,180,0.4)"),
                hovertemplate="<b>Masked (Real)</b><br>t=%{x:.3f}<br>V=%{y:.4f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=t[masked], y=V.imag[masked],
                mode="markers", name="Masked (Imag)",
                marker=dict(size=8, color="rgba(180,180,180,0.4)"),
                hovertemplate="<b>Masked (Imag)</b><br>t=%{x:.3f}<br>V=%{y:.4f}<extra></extra>",
            ))
        fig.update_layout(
            xaxis_title="Time (µs)",
            yaxis_title="Signal (a.u.)",
            margin=dict(l=50, r=20, t=20, b=40),
            legend=dict(orientation="h", y=-0.2),
            height=300,
            dragmode="select",
            clickmode="event+select",
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
        duration=5000,
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
    Output({"type": "dataset-dl-modal", 'page': page_id}, "opened"),
    Output({"type": "dataset-dl-store",'page': page_id}, "data"),
    Input("dd-download-btn", "n_clicks"),
    State("dd-dataset-id", "data"),
    prevent_initial_call=True,
)
def toggle_download_modal(n_clicks,ds_id):
    
    if n_clicks is None:
        return False,dash.no_update
    return True,ds_id
    

@callback(
    Output("dd-name", "disabled"),
    Output("dd-project", "disabled"),
    Output("dd-sample", "disabled"),
    Output("dd-exp", "disabled"),
    Output("dd-measured_at", "readOnly"),

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
    return disabled, disabled, disabled, disabled,disabled, button_icon

@callback(
        Output("dd-notification", "children",allow_duplicate=True),
        Input("dd-basic-info-editable", "n_clicks"),
        State("dd-dataset-id", "data"),
        State("dd-name", "value"),
        State("dd-project", "value"),
        State("dd-sample", "value"),
        State("dd-exp", "value"),
        State("dd-measured_at", "value"),
        prevent_initial_call=True,
)
def save_basic_info(n_clicks, dataset_id, name, project, sample, exp,measured_at):
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
        if measured_at:
            measured_at_dt = dt.datetime.fromisoformat(measured_at)
            dataset.measured_at = measured_at_dt
        check_delays(dataset)
        session.commit()
        session.close()
        return _alert("Basic information saved successfully.", "green", "Saved")
    except Exception as exc:
        return _alert(f"Error saving basic information: {exc}", "red", "Save Error")
    

@callback(
    Output({"type": "delays-grid",'page': page_id}, "columnDefs"),
    Output("dd-delays-editable", "children"),
    Output({"type": "tmin", 'page': page_id}, "disabled"),
    Input("dd-delays-editable", "n_clicks"),
    prevent_initial_call=True,
)
def make_delays_editable_save(n_clicks):
    # Toggle disabled state of delays textarea
    disabled = n_clicks % 2 == 0  # Even clicks -> disabled, Odd clicks -> enabled
    if disabled:
        delays = delays_columnDefs(False)
        button_icon = DashIconify(icon='mdi:edit',)
    else:
        delays = delays_columnDefs(True)
        button_icon = DashIconify(icon='mdi:content-save',)
    return delays, button_icon,disabled

@callback(
    Output("dd-notification", "children",allow_duplicate=True),
    # Output({"type": "tmin", 'page': page_id}, "value",allow_duplicate=True),
    Input("dd-delays-editable", "n_clicks"),
    State("dd-dataset-id", "data"),
    State({"type": "delays-grid",'page': page_id}, "rowData"),
    State({"type": "tmin", 'page': page_id}, "value"),
    prevent_initial_call=True,
)
def save_delays(n_clicks,dataset_id,rowData,tmin):
    if n_clicks % 2 != 0:
        # If button is in "Edit" mode, do not save
        return dash.no_update
    try:
        session = get_session()
        dataset = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset is None:
            session.close()
            return _alert("Dataset not found in the database.", "red", "Save Error")
        new_delays = {row["parameter"]: row["value"] for row in rowData}
        dataset.delays = new_delays
        t = np.array(dataset.t)

        if tmin/1e3 != t[0]:
            tmin_shift = tmin/1e3 - t[0]
            print(f"Applying tmin shift of {tmin_shift} ns to dataset {dataset_id}")
            new_t = np.array(dataset.t) + tmin_shift
            dataset.t = new_t.tolist() 

        
        session.commit()
        session.close()
        return _alert("Delays saved successfully.", "green", "Saved")#,0
    except Exception as exc:
        return _alert(f"Error saving delays: {exc}", "red", "Save Error")#,dash.no_update

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


@callback(
    Output({'type': 'dataset-store', 'page': page_id}, 'data', allow_duplicate=True),
    Input({"type": "tmin", 'page': page_id}, "value"),
    State({'type': 'dataset-store', 'page': page_id}, 'data'),
    prevent_initial_call=True,
)
def update_tmin_dd(tmin, store):
    if store is None:
        return dash.no_update
    store = dict(store)
    store['tmin'] = tmin / 1e3  # ns → µs
    return store


@callback(
    Output({'type': 'data-viewer-plot', 'page': page_id}, 'figure', allow_duplicate=True),
    Input({'type': 'dataset-store', 'page': page_id}, 'data'),
    Input({'type': 'data-masking-enabled', 'page': page_id}, 'checked'),
    prevent_initial_call=True,
)
def rebuild_signal_figure_dd(store, masking_enabled):
    if store is None:
        return dash.no_update
    return plot_upload(store, correct_phase=False, masking_enabled=masking_enabled or False)


@callback(
    Output("dd-redirect", "pathname"),
    Output({"type": "fit-dl-modal", 'page': page_id}, "opened", allow_duplicate=True),
    Output({"type": "fit-dl-store", 'page': page_id}, "data", allow_duplicate=True),
    Input("dd-fits-table", "cellRendererData"),
    State("dd-fits-table", "rowData"),
    prevent_initial_call=True,
)
def fit_buttons(cellRendererData, rowData):
    """Navigate to the fit page or open the download modal."""
    if cellRendererData is None or cellRendererData.get('colId') != 'Open':
        return dash.no_update
    action = (cellRendererData.get('value') or {}).get('action')
    rowIndex = cellRendererData.get('rowIndex', None)
    selected_row = rowData[rowIndex] if rowIndex is not None and rowIndex < len(rowData) else None
    fit_id = selected_row.get('id') if selected_row else None
    if fit_id is None:
        return dash.no_update
    if action != 'left':  # right button -> download
        return dash.no_update, True, fit_id
    return f'/fit/{fit_id}', dash.no_update, dash.no_update


@callback(
    Output("dd-notification", "children", allow_duplicate=True),
    Input("dd-save-mask-btn", "n_clicks"),
    State({'type': 'dataset-store', 'page': page_id}, 'data'),
    State("dd-dataset-id", "data"),
    prevent_initial_call=True,
)
def dd_save_mask(_, store, dataset_id):
    masked_indices = (store or {}).get('masked_indices', [])
    try:
        session = get_session()
        dataset = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset is None:
            session.close()
            return _alert("Dataset not found.", "red", "Save Error")

        n = len(dataset.t)
        mask = [True] * n
        for i in (masked_indices or []):
            if 0 <= i < n:
                mask[i] = False
        dataset.mask = mask
        session.commit()
        session.close()
        masked_count = sum(1 for v in mask if not v)
        return _alert(f"Mask saved — {masked_count} point(s) masked.", "green", "Saved")
    except Exception as exc:
        return _alert(f"Error saving mask: {exc}", "red", "Save Error")
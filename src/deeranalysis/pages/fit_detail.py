"""
A detauled fit viewer page for displaying fit results, along with relevant metadata and visualizations. Not designed to compare fits.
Accessible at /fit/<fit_id>.

"""

import dash
from dash import html, dcc, callback, Input, Output, State, clientside_callback
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash_ag_grid as dag
from dash_iconify import DashIconify
import plotly.graph_objs as go
import numpy as np
import json

from deeranalysis.utils.database import get_session, Dataset,check_delays, Fit
from deeranalysis.utils import create_subplot_figure,plotly_deerlab
from deeranalysis.components.metadata_table import build_metadata_section,build_delays_table, metadata_long_values_model,build_delays_AGgrid,delays_columnDefs
from deeranalysis.components.download_modal import create_fit_download_modal

dash.register_page(__name__, path_template="/fit/<fit_id>")
page_id = "fit-detail"




def layout(fit_id=None):

    if fit_id is None:
        return _error_page("No fit ID provided in URL.")
    
    try:
        session = get_session()
        if session is None:
            return _error_page("Database is not available.")
        fit = session.query(Fit).filter_by(id=fit_id).first()
        ds_id = fit.dataset_id if fit else None
        dataset = session.query(Dataset).filter_by(id=ds_id).first() if ds_id else None
        session.close()
    except Exception as e:
        return _error_page(f"Error accessing database: {str(e)}")
    

    if fit is None:
        return _error_page(f"Fit with ID {fit_id} not found.")
    
    output = html.Div([
        dcc.Store(id='fd-fit-id',data=int(fit_id)),
        deletion_modal(),
        create_fit_download_modal(page_id=page_id),

        # ---- header ---------------------------------------------------------
        dmc.Group([
                dmc.Breadcrumbs(
                    children=[
                        dmc.Anchor("Datasets", href="/", underline=False),
                        dmc.Anchor(f"Dataset {ds_id}", href=f"/dataset/{ds_id}", underline=False),
                        dmc.Anchor(f"Fit - {fit_id}", href=f"/fit/{fit_id}", underline=False),

                    ],
                    separator="->",
                ),
            dmc.TextInput(
                id="fd-fit-name",
                value=fit.name or "",
                readOnly=True,
                variant="unstyled",
                styles={
                    "input": {
                        "fontSize": "2.5rem",  # Matches dmc.Title order=1
                        "fontWeight": 700,
                        "color": "#212529",
                        "opacity": 1,
                        "cursor": "default",
                        "lineHeight": 1.2,
                        "letterSpacing": "-0.02em",
                        "marginBottom": "0.5rem"
                    }
                },
            ),
            dmc.ActionIcon(
                DashIconify(icon="mdi:pencil", width=18),
                variant="subtle",
                id="fd-edit-name-btn",
                size="lg",
            ),
            dmc.Space(style={"flex": 1}),
            dmc.Button(
                "Download",
                id="fit-dl-btn",
                color="blue",
                leftSection=DashIconify(icon="mdi:download", width=18),
            ),
            dmc.ActionIcon(
                DashIconify(icon="mdi:trash", width=18),
                variant="outline",
                color="red",
                id="fd-delete-btn",
            ),
        ], mb="md"),
        dmc.Divider(mb="md"),

        # ---- notification area ----------------------------------------------
        html.Div(id="dd-notification"),

        # ---- Content -------------------------------------------------------
        dbc.Row([
            dbc.Col([
                _basic_fit_info(fit),
                _fit_description(fit),
                _fit_gof_stats(fit),
                _fit_dist_stats(fit),
            ], width=6),
            dbc.Col([
            _fit_plot(fit,dataset),
            ], width=6)
        ])
    ], style={"padding": "20px"})

    return output







# ---------------------------------------------------------------------------
# Helpers
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
            dmc.Title("Fit Not Found", order=2),
        ], mb="md"),
        dmc.Alert(message, color="red", title="Error"),
    ], style={"padding": "20px"})


def deletion_modal():
    return dmc.Modal(
            id="fd-delete-modal",
            title="Confirm Deletion",
            children=[
                html.P("Are you sure you want to delete this fit? This action cannot be undone."),
                dmc.Group([
                    dmc.Button("Cancel", id="fd-cancel-delete-btn"),
                    dmc.Button("Delete", id="fd-confirm-delete-btn", color="red"),
                ], justify="flex-end", mt="md"),
            ],
            centered=True,
        )

def _basic_fit_info(fit):
    input_styles = {"input": {"backgroundColor": "#fff", "color": "#212529", "opacity": 1, "cursor": "default"}}
    return dmc.Paper([
        dmc.Group([
            dmc.Title("Basic Fit Information", order=4, mb="sm"),
            dmc.Button(
                DashIconify(icon="tabler:chevron-down"),
                id="fd-basic-toggle",
                variant="subtle",
                color="gray",
                size="sm",
                p=0,
            ),
        ], justify="space-between", mb="sm"),
        dmc.Collapse(
            dmc.Grid([
                dmc.GridCol(
                    dmc.TextInput(
                        id="fd-engine",
                        label="Engine",
                        value=fit.engine or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.TextInput(
                        id="fd-fit_type",
                        label="Fit Type",
                        value=fit.fit_type or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.TextInput(
                        id="fd-dist_model",
                        label="Parameteric Distance Model (if applicable)",
                        value=fit.dist_model or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.TextInput(
                        id="fd-bg_model",
                        label="Background Model",
                        value=fit.bg_model or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.TextInput(
                        id="fd-pathways",
                        label="Pathways Used",
                        value=fit.pathways or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    dmc.DateTimePicker(
                        id="fd-created_at",
                        label="Created At",
                        value=fit.created_at or "",
                        readOnly=True,
                        variant="default",
                        styles=input_styles,
                    ),
                    span=6,
                ),
            ]),
            id="fd-basic-collapse",
            opened=True,
        ),
    ], p="md", mb="md", withBorder=True, radius="md")


def _fit_description(fit):
    return dmc.Paper([
        dmc.Group([
            dmc.Title("Fit Description", order=4),
            dmc.Button(
                DashIconify(icon="tabler:chevron-down"),
                id="fd-description-toggle",
                variant="subtle",
                color="gray",
                size="sm",
                p=0,
            ),
        ], justify="space-between", mb="sm"),
        dmc.Collapse(
            dmc.CodeHighlight(fit.model_description or "No description provided.", language="bash"),
            id="fd-description-collapse",
            opened=True,
        ),
    ], p="md", mb="md", withBorder=True, radius="md")


def _fit_gof_stats(fit):
    if not fit.gof:
        content = dmc.Text("No goodness-of-fit metrics available.", style={"whiteSpace": "pre-wrap"})
    else:

        gof_items = [f"{key}: {value:.4f}" for key, value in fit.gof.items()]
        content = dmc.Text("\n".join(gof_items), style={"whiteSpace": "pre-wrap"})

    return dmc.Paper([
        dmc.Group([
            dmc.Title("Goodness-of-Fit Metrics", order=4, mb="sm"),
            dmc.Button(
                DashIconify(icon="tabler:chevron-down"),
                id="fd-gof-toggle",
                variant="subtle",
                color="gray",
                size="sm",
                p=0,
            ),
        ], justify="space-between", mb="sm"),
        dmc.Collapse(
            content,
            id="fd-gof-collapse",
            opened=True,
        ),
    ], p="md", mb="md", withBorder=True, radius="md")

def _fit_dist_stats(fit):
    if not fit.dist_stats:
        content = "No distance distribution statistics available."
    else:
        dist_stats_items = [f"{key}: {value:.4f}" for key, value in fit.dist_stats.items()]
        content = "\n".join(dist_stats_items)

    return dmc.Paper([
        dmc.Group([
            dmc.Title("Distance Distribution Statistics", order=4, mb="sm"),
            dmc.Button(
                DashIconify(icon="tabler:chevron-down"),
                id="fd-dist-toggle",
                variant="subtle",
                color="gray",
                size="sm",
                p=0,
            ),
        ], justify="space-between", mb="sm"),
        dmc.Collapse(
            dmc.Text(content, style={"whiteSpace": "pre-wrap"}),
            id="fd-dist-collapse",
            opened=True,
        ),
    ], p="md", mb="md", withBorder=True, radius="md")

@callback(
    Output("fd-fit-name", "readOnly"),
    Output("fd-fit-name", "variant"),
    Output("fd-fit-name", "styles"),
    Output("fd-edit-name-btn", "children"),
    Input("fd-edit-name-btn", "n_clicks"),
    State("fd-fit-name", "readOnly"),
    State("fd-fit-name", "value"),
    State("fd-fit-id", "data"),
    prevent_initial_call=True,
)
def toggle_name_edit(n_clicks, is_readonly, fit_name, fit_id):
    title_styles = {
        "input": {
            "fontSize": "2.5rem",
            "fontWeight": 700,
            "color": "#212529",
            "opacity": 1,
            "cursor": "default",
            "lineHeight": 1.2,
            "letterSpacing": "-0.02em",
            # "marginBottom": "0.5rem",
        }
    }
    edit_styles = {
        "input": {
            "fontSize": "2.5rem",
            "fontWeight": 700,
            "color": "#212529",
            "lineHeight": 1.2,
            "letterSpacing": "-0.02em",
            # "marginBottom": "0.5rem",
        }
    }
    if is_readonly:
        return False, "default", edit_styles, DashIconify(icon="mdi:check", width=18)
    else:
        # Edit the fit name in the database
        session = get_session()
        fit = session.query(Fit).filter_by(id=fit_id).first()
        fit.name = fit_name
        session.commit()
        session.close()

        return True, "unstyled", title_styles, DashIconify(icon="mdi:pencil", width=18)

@callback(
    Output("fd-description-collapse", "opened"),
    Input("fd-description-toggle", "n_clicks"),
    State("fd-description-collapse", "opened"),
    prevent_initial_call=True,
)
def toggle_description_collapse(n_clicks, opened):
    return not opened

@callback(
    Output("fd-basic-collapse", "opened"),
    Input("fd-basic-toggle", "n_clicks"),
    State("fd-basic-collapse", "opened"),
    prevent_initial_call=True,
)
def toggle_basic_collapse(n_clicks, opened):
    return not opened

@callback(
    Output("fd-gof-collapse", "opened"),
    Input("fd-gof-toggle", "n_clicks"),
    State("fd-gof-collapse", "opened"),
    prevent_initial_call=True,
)
def toggle_gof_collapse(n_clicks, opened):
    return not opened

@callback(
    Output("fd-dist-collapse", "opened"),
    Input("fd-dist-toggle", "n_clicks"),
    State("fd-dist-collapse", "opened"),
    prevent_initial_call=True,
)
def toggle_dist_collapse(n_clicks, opened):
    return not opened

@callback(
    Output("fd-plot-collapse", "opened"),
    Input("fd-plot-toggle", "n_clicks"),
    State("fd-plot-collapse", "opened"),
    prevent_initial_call=True,
)
def toggle_plot_collapse(n_clicks, opened):
    return not opened

def _fit_plot(fit,dataset):
    if not fit.t or not fit.model:
        content = dmc.Text("No time-domain data available for plotting.")
    else:
        fit_dict = _fits_and_dataset_to_dict(dataset, fit)
        fig = plotly_deerlab(fit_dict)
        content = dcc.Graph(figure=fig, config={"displayModeBar": False})

    return dmc.Paper([
        dmc.Group([
            dmc.Title("Fit Plot", order=4, mb="sm"),
            dmc.Button(
                DashIconify(icon="tabler:chevron-down"),
                id="fd-plot-toggle",
                variant="subtle",
                color="gray",
                size="sm",
                p=0,
            ),
        ], justify="space-between", mb="sm"),
        dmc.Collapse(
            content,
            id="fd-plot-collapse",
            opened=True,
        ),
    ], p="md", mb="md", withBorder=True, radius="md")   


def _fits_and_dataset_to_dict(dataset, fit=None):
    output = {}
    output['t'] = np.array(dataset.t, dtype=float)
    output['V'] = np.array(dataset.V, dtype=float)
    output['V'] /= output['V'].max()
    output['model'] = np.array(fit.model, dtype=float)
    output['r'] = np.array(fit.r, dtype=float)
    output['P'] = np.array(fit.P_model, dtype=float)
    return output

# ---- Download and Deletion Callbacks -------------------------------------------------------

@callback(
    Output({"type": "fit-dl-modal",'page': page_id}, "opened"),
    Output({"type": "fit-dl-store",'page': page_id}, "data"),
    Input("fit-dl-btn", 'n_clicks'),
    State('fd-fit-id', 'data'),
    prevent_initial_call=True
)
def download_fit(n_clicks, fit_id):
    print(f"Download button clicked for fit_id: {fit_id} with n_clicks: {n_clicks}")
    if n_clicks is None or not fit_id:
        return False, dash.no_update
    
    return True, fit_id

@callback(
    Output("fd-delete-modal", "opened"),
    Input("fd-delete-btn", "n_clicks"), 
    Input("fd-cancel-delete-btn", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_delete_modal(n_delete, n_cancel):
    
    ctx = dash.callback_context
    if not ctx.triggered:
        
        return False
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id == "fd-delete-btn":
        return True
    else:
        return False
    
@callback(
    Output("fd-notification", "children",allow_duplicate=True),
    Output("fd-delete-modal", "opened",allow_duplicate=True),
    Input("fd-confirm-delete-btn", "n_clicks"),
    State("fd-fit-id", "data"),
    prevent_initial_call=True,
)
def delete_fit(n_clicks,fit_id):
    try:
        session = get_session()
        fit = session.query(Fit).filter_by(id=fit_id).first()
        if fit is None:
            session.close()
            return _alert("Dataset not found in the database.", "red", "Delete Error")

        session.delete(fit)
        session.commit()
        session.close()
        return dcc.Location(pathname="/", id="fd-redirect-home"), False
    except Exception as exc:
        return _alert(f"Error deleting dataset: {exc}", "red", "Delete Error"), False

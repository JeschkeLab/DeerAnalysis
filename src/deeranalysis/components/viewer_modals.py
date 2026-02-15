import dash
from dash import html, dcc, callback, Input, Output, State
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset
import dash_ag_grid as dag  



def create_viewer_modal(id="viewer-modal", title="Dataset Viewer"):
    """
    Creates a reusable modal component for viewing dataset primary data traces.
    Basd on a dash-mantine modal, with a figure inside and a close button.

    Parameters
    ----------
    id : str, optional
        _description_, by default "viewer-modal"
    title : str, optional
        _description_, by default "Dataset Viewer"

    Returns
    -------
    _type_
        _description_
    """

    return dmc.Modal(
        title=title,
        id=id,
        size="80%",
        opened=False,  # Control visibility with a callback
        children=[
            dcc.Graph(id=f"{id}-figure", 
                      figure = {
                          "data": [],
                          "layout": {
                              "title": "Dataset Primary Data",
                              "xaxis": {"title": "Time (ns)"},
                              "yaxis": {"title": "Intensity (a.u.)"},
                              "template": "plotly_white"
                          }
                      },
                      style={"height": "70vh", "overflowY": "auto"}),
            dmc.Group(
                [dmc.Button("Close", id="close-viewer-btn")],
                justify="flex-end",
                className="mt-2"
            ),
        ],
    )

@callback(
    Output("viewer-modal", "opened",allow_duplicate=True),
    Input("close-viewer-btn", "cellClicked"),
    prevent_initial_call=True
)
def toggle_viewer_modal(n_clicks):
    if n_clicks:
        return False
    return dash.no_update
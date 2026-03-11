import dash
from dash import html, dcc, callback, Input, Output, State, MATCH
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import io
import traceback
from deeranalysis.utils.io import datasetSQL_to_file
from deeranalysis.utils.database import get_session, Dataset


FORMAT_OPTIONS = [
    {"value": "bruker", "label": "Bruker (.DTA/.DSC)"},
    {"value": "hdf5",   "label": "HDF5 (.h5)"},
    {"value": "matlab", "label": "Matlab (.mat)"},
    {"value": "csv",    "label": "CSV (.csv)"},
]

EXTENSIONS = {
    "bruker": ".DTA",
    "hdf5":   ".h5",
    "matlab": ".mat",
    "csv":    ".csv",
}

DOWNLOAD_FORMAT_OPTIONS = [
    {"value": "hdf5",   "label": "HDF5 (.h5)"},
    {"value": "matlab", "label": "Matlab (.mat)"},
    {"value": "csv",    "label": "CSV (.csv)"},
]

# ---------------------------------------------------------------------------
# Component factories
# ---------------------------------------------------------------------------
# All inner component IDs use the pattern-matching dict form
#   {"type": "<type-key>", "index": <id>}
# so that a single set of callbacks covers every instance, regardless of
# how many pages mount these modals or what `id` they pass in.
# ---------------------------------------------------------------------------

def create_dataset_download_modal(page_id="dataset-download-modal"):
    """
    Modal for downloading a dataset.

    The modal owns a hidden ``dcc.Store`` that holds the dataset id to export.
    Open the modal via::

        Output({"type": "dataset-dl-modal",  "index": "<id>"}, "opened") -> True
        Output({"type": "dataset-dl-store",  "index": "<id>"}, "data")   -> dataset_id

    Parameters
    ----------
    id : str
        Unique prefix for this instance. Use different values on each page to
        avoid id collisions.
    """
    return html.Div([
        dcc.Store(id={"type": "dataset-dl-store", "page": page_id}, data=None),
        dmc.Modal(
            id={"type": "dataset-dl-modal",  "page": page_id},
            title=dmc.Text("Download Dataset", fw=600, size="lg"),
            size="md",
            opened=False,
            children=[
                dmc.Stack([
                    html.Div(id={"type": "dataset-dl-alert", "page": page_id}),
                    dmc.Select(
                        id={"type": "dataset-dl-format", "page": page_id},
                        label="File format",
                        description="Choose the format for the exported file.",
                        data=FORMAT_OPTIONS,
                        value="hdf5",
                        allowDeselect=False,
                        w="100%",
                    ),
                    dmc.TextInput(
                        id={"type": "dataset-dl-filename", "page": page_id},
                        label="Filename",
                        description="Enter the filename (without extension).",
                        placeholder="dataset",
                        w="100%",
                    ),
                    dcc.Download(id={"type": "dataset-dl-download", "page": page_id}),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Cancel",
                                id={"type": "dataset-dl-cancel", "page": page_id},
                                variant="subtle",
                                color="gray",
                            ),
                            dmc.Button(
                                "Download",
                                id={"type": "dataset-dl-btn", "page": page_id},
                                leftSection=DashIconify(icon="mdi:download-outline"),
                            ),
                        ],
                        justify="flex-end",
                        mt="md",
                    ),
                ], gap="sm"),
            ],
        ),
    ])


def create_fit_download_modal(page_id="fit-download-modal"):
    """
    Modal for downloading a fit result.

    The modal owns a hidden ``dcc.Store`` that holds the fit id to export.
    Open the modal via::

        Output({"type": "fit-dl-modal",  "index": "<id>"}, "opened") -> True
        Output({"type": "fit-dl-store",  "index": "<id>"}, "data")   -> fit_id

    Parameters
    ----------
    id : str
        Unique prefix for this instance. Use different values on each page to
        avoid id collisions.
    """
    return html.Div([
        dcc.Store(id={"type": "fit-dl-store", "page": page_id}, data=None),
        dmc.Modal(
            id={"type": "fit-dl-modal", "page": page_id},
            title=dmc.Text("Download Fit", fw=600, size="lg"),
            size="md",
            opened=False,
            children=[
                dmc.Stack([
                    dmc.Select(
                        id={"type": "fit-dl-format", "page": page_id},
                        label="File format",
                        description="Choose the format for the exported fit result.",
                        data=DOWNLOAD_FORMAT_OPTIONS,
                        value="hdf5",
                        allowDeselect=False,
                        w="100%",
                    ),
                    dmc.TextInput(
                        id={"type": "fit-dl-filename", "page": page_id},
                        label="Filename",
                        description="Enter the filename (without extension).",
                        placeholder="fit_result",
                        w="100%",
                    ),
                    dmc.Checkbox(
                        id={"type": "fit-dl-include-uncert", "page": page_id},
                        label="Include uncertainty estimates (if available)",
                        value=True,
                    ),
                    dmc.Checkbox(
                        id={"type": "fit-dl-resample_deernet", "page": page_id},
                        label="Resample the DeerNet fit to the original dataset's time axis (if applicable)",
                        value=True,
                        
                    ),
                    dcc.Download(id={"type": "fit-dl-download", "page": page_id}),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Cancel",
                                id={"type": "fit-dl-cancel", "page": page_id},
                                variant="subtle",
                                color="gray",
                            ),
                            dmc.Button(
                                "Download",
                                id={"type": "fit-dl-btn", "page": page_id},
                                leftSection=DashIconify(icon="mdi:download-outline"),
                            ),
                        ],
                        justify="flex-end",
                        mt="md",
                    ),
                ], gap="sm"),
            ],
        ),
    ])


# ---------------------------------------------------------------------------
# Pattern-matched callbacks — registered once, cover every mounted instance
# ---------------------------------------------------------------------------

@callback(
    Output({"type": "dataset-dl-modal", "page": MATCH}, "opened", allow_duplicate=True),
    Input({"type": "dataset-dl-cancel", "page": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def _close_dataset_download_modal(n_clicks):
    return False if n_clicks else dash.no_update


@callback(
    Output({"type": "fit-dl-modal", "page": MATCH}, "opened", allow_duplicate=True),
    Input({"type": "fit-dl-cancel", "page": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def _close_fit_download_modal(n_clicks):
    return False if n_clicks else dash.no_update


@callback(
    Output({"type": "dataset-dl-download", "page": MATCH}, "data"),
    Output({"type": "dataset-dl-modal",    "page": MATCH}, "opened", allow_duplicate=True),
    Output({"type": "dataset-dl-alert", "page": MATCH}, "children"),
    Input({"type": "dataset-dl-btn",       "page": MATCH}, "n_clicks"),
    State({"type": "dataset-dl-store",     "page": MATCH}, "data"),
    State({"type": "dataset-dl-format",    "page": MATCH}, "value"),
    State({"type": "dataset-dl-filename",  "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def _download_dataset(n_clicks, dataset_id, fmt, filename):
    if not n_clicks or dataset_id is None:
        return dash.no_update, dash.no_update

    filename = (filename or "dataset").strip() or "dataset"
    ext = EXTENSIONS.get(fmt, "")
    full_name = filename + ext

    # get dataset entry
    session = get_session()
    dataset = session.query(Dataset).filter_by(id=dataset_id).first()
    session.close()

    # Create file content in memory and send as download

    if fmt == "bruker":
        alert = dmc.Alert(
            "Bruker export is not yet implemented. Please choose another format.",
            color="red",
            variant="filled",
        )
        return dash.no_update, True, alert
    elif fmt == "hdf5":
        buf = io.BytesIO()
        try:
            datasetSQL_to_file(buf, dataset, "h5")

        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            alert = dmc.Alert(
                f"HDF5 export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
        
        return dcc.send_bytes(buf.getvalue(), full_name), True, dash.no_update
    elif fmt == "matlab":
        buf = io.BytesIO()
        try:
            datasetSQL_to_file(buf, dataset, "mat")
        except Exception as e:
            alert = dmc.Alert(
                f"MATLAB export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
        return dcc.send_bytes(buf.getvalue(), full_name), True, dash.no_update
    elif fmt == "csv":
        buf = io.StringIO()
        try:
            datasetSQL_to_file(buf, dataset, fmt)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            alert = dmc.Alert(
                f"CSV export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert

        return dcc.send_string(buf.getvalue(), full_name), True, dash.no_update
    

    return dash.no_update, False, dash.no_update


@callback(
    Output({"type": "fit-dl-download", "index": MATCH}, "data"),
    Output({"type": "fit-dl-modal",    "index": MATCH}, "opened", allow_duplicate=True),
    Input({"type": "fit-dl-btn",       "index": MATCH}, "n_clicks"),
    State({"type": "fit-dl-store",     "index": MATCH}, "data"),
    State({"type": "fit-dl-format",    "index": MATCH}, "value"),
    State({"type": "fit-dl-filename",  "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def _download_fit(n_clicks, fit_id, fmt, filename):
    if not n_clicks or fit_id is None:
        return dash.no_update, dash.no_update

    filename = (filename or "fit_result").strip() or "fit_result"
    ext = EXTENSIONS.get(fmt, "")
    full_name = filename + ext

    # TODO: implement per-format export logic using fit_id
    # Example skeleton:
    #   from deeranalysis.utils.database import get_session, Fit
    #   session = get_session()
    #   fit = session.query(Fit).filter_by(id=fit_id).first()
    #   session.close()
    #   if fmt == "csv":
    #       content = fit_to_csv(fit)
    #       return dcc.send_string(content, full_name), False
    #   ...

    return dash.no_update, False

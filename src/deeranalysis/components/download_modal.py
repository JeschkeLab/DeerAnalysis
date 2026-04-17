import dash
from dash import html, dcc, callback, Input, Output, State, MATCH
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import io
import traceback
from deeranalysis.utils.io import datasetSQL_to_file,fitSQL_to_file
from deeranalysis.utils.database import get_session, Dataset,Fit
from deerlab import save, json_loads
import sys
import os

def _is_pywebview():
    return os.environ.get('DEERANALYSIS_PYWEBVIEW') == '1'

DATASET_DOWNLOAD_FORMAT_OPTIONS = [
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

FIT_DOWNLOAD_FORMAT_OPTIONS = [
    {"value": "dl-hdf5",   "label": "DeerLab - HDF5 (.h5)"},
    {"value": "hdf5",   "label": "HDF5 (.h5)"},
    {"value": "matlab", "label": "Matlab (.mat)"},
    {"value": "csv",    "label": "CSV (.csv)"},
]
FILE_TYPE_FILTERS = {
    ".h5":  ("HDF5 files (*.h5)",),
    ".mat": ("MATLAB files (*.mat)",),
    ".csv": ("CSV files (*.csv)",),
    ".zip": ("ZIP archives (*.zip)",),
    ".DTA": ("Bruker files (*.DTA)",),
}


FitDownload_Context = """
The fit result can be downloaded in the following formats:

1. **DeerLab - HDF5 (.h5)**: Complete fit data including DeerLab-specific metadata and uncertainty information. 
This format is ideal for users who wish to preserve all details of the fit and may want to re-import it into DeerLab later, and investigate different uncertainty values. 
Import into DeerLab using the `dl.load` function (DeerLab v1.2.0 or later is required).

2. **HDF5 (.h5)**: Standard HDF5 format compatible with multiple software packages.
This option provides a more generic export that can be read by various tools, but may not include all DeerLab-specific metadata or uncertainty details. 
The output includes:

* Time axis, 
* Fitted model,
* Distance axis,
* Distance distribution,
* 95% CI Uncertainty estimates for the distance distribution (if available).

3. **Matlab (.mat)**: MATLAB-compatible format for use in MATLAB environments.
This is the same as for the HDF5 option but in a .mat file. It can be imported into MATLAB using the `load` function, and is suitable for users who primarily work in MATLAB.

4. **CSV (.csv)**: Comma-separated values format for easy import into spreadsheet applications.
This option exports the fit data into CSV files, which can be easily opened in Excel or other spreadsheet software. 
However, it is not possible to export as a single CSV file, so the output will be a ZIP archive containing multiple CSVs.

* `[file]_t.csv`: Contains the time axis and fitted model values.
* `[file]_dd.csv`: Contains the distance axis and distance distribution values.
    
If a DeerNet fit is to be exported, the exported time axis and fitted model will be resampled to match the original dataset's time axis.
"""

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
            withinPortal=False,
            children=[
                dmc.Stack([
                    html.Div(id={"type": "dataset-dl-alert", "page": page_id}),
                    dmc.Select(
                        id={"type": "dataset-dl-format", "page": page_id},
                        label="File format",
                        description="Choose the format for the exported file.",
                        data=DATASET_DOWNLOAD_FORMAT_OPTIONS,
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
                        style={"display": "none"} if _is_pywebview() else None,
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
                    html.Div(id={"type": "fit-dl-alert", "page": page_id}),
                    dmc.Group([
                        dmc.Select(
                            id={"type": "fit-dl-format", "page": page_id},
                            label="File format",
                            description="Choose the format for the exported fit result.",
                            data=FIT_DOWNLOAD_FORMAT_OPTIONS,
                            value="hdf5",
                            allowDeselect=False,
                            w="100%",
                            style={"flex": 1},
                        ),
                        dmc.Button(
                            DashIconify(icon="mdi:information-outline",width=20,height=20,),
                            id={"type": "fit-dl-info-btn", "page": page_id},
                            variant="subtle",
                            color="blue",
                            # title="Format information",
                            mt=2,
                            p=0,
                        ),
                    ], w="100%", align="flex-end",gap="xs"),
                    dmc.TextInput(
                        id={"type": "fit-dl-filename", "page": page_id},
                        label="Filename",
                        description="Enter the filename (without extension).",
                        placeholder="fit_result",
                        w="100%",
                        style={"display": "none"} if _is_pywebview() else None,
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
        dmc.Modal(
            id={"type": "fit-dl-info-modal", "page": page_id},
            title=dmc.Text("Download Format Information", fw=600, size="lg"),
            size="50%",
            opened=False,
            children=[
                dmc.TypographyStylesProvider(
                    dcc.Markdown(FitDownload_Context, dangerously_allow_html=False, id="default"),
                ),
            ],
        ),
    ])

def _save_file_native(content: bytes, suggested_name: str):
    """Use pywebview's native save dialog to write a file."""
    import webview
    # webview.windows[0] is available after webview.start()
    ext = os.path.splitext(suggested_name)[1]
    file_types = FILE_TYPE_FILTERS.get(ext, ("All files (*.*)",))

    result = webview.windows[0].create_file_dialog(
        webview.FileDialog.SAVE,
        save_filename=suggested_name,
        file_types=file_types,
    )
    if not result:
        return False

    path = result if isinstance(result, str) else result[0]
    if isinstance(content, str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        with open(path, 'wb') as f:
            f.write(content)
    return True
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
    Output({"type": "fit-dl-info-modal", "page": MATCH}, "opened", allow_duplicate=True),
    Input({"type": "fit-dl-info-btn", "page": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def _open_fit_info_modal(n_clicks):
    return True if n_clicks else dash.no_update


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
    print(f"Triggered dataset download callback with dataset_id={dataset_id}, fmt={fmt}, filename={filename}")
    if not n_clicks or dataset_id is None:
        print("Download callback triggered without clicks or dataset_id")
        return dash.no_update, dash.no_update, dash.no_update

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
        
    elif fmt == "matlab":
        buf = io.BytesIO()
        try:
            datasetSQL_to_file(buf, dataset, "matlab")
        except Exception as e:
            alert = dmc.Alert(
                f"MATLAB export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
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

        
    
    if _is_pywebview():
        _save_file_native(buf.getvalue(), full_name)
        return dash.no_update, True, dash.no_update
    elif isinstance(buf, io.BytesIO):
        return dcc.send_bytes(buf.getvalue(), full_name), True, dash.no_update
    elif isinstance(buf, io.StringIO):
        return dcc.send_string(buf.getvalue(), full_name), True, dash.no_update
    return dash.no_update, False, dash.no_update


@callback(
    Output({"type": "fit-dl-download", "page": MATCH}, "data"),
    Output({"type": "fit-dl-modal",    "page": MATCH}, "opened", allow_duplicate=True),
    Output({"type": "fit-dl-alert", "page": MATCH}, "children"),
    Input({"type": "fit-dl-btn",       "page": MATCH}, "n_clicks"),
    State({"type": "fit-dl-store",     "page": MATCH}, "data"),
    State({"type": "fit-dl-format",    "page": MATCH}, "value"),
    State({"type": "fit-dl-filename",  "page": MATCH}, "value"),
    prevent_initial_call=True,
)
def _download_fit(n_clicks, fit_id, fmt, filename):
    print(f"Triggered fit download callback with fit_id={fit_id}, fmt={fmt}, filename={filename}")
    if not n_clicks or fit_id is None:
        return dash.no_update, dash.no_update

    filename = (filename or "fit_result").strip() or "fit_result"
    ext = EXTENSIONS.get(fmt, "")
    full_name = filename + ext

    session = get_session()
    fit_entry = session.query(Fit).filter_by(id=fit_id).first()
    dataset_entry = session.query(Dataset).filter_by(id=fit_entry.dataset_id).first()
    session.close()

    if fmt == "dl-hdf5":
        # Check that the data entry in the fit_entry is not None
        if fit_entry.data is None:
            alert = dmc.Alert(
                "No data available for this fit result. Cannot export to DeerLab HDF5 format.",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
        
        full_name = filename + ext
        buf = io.BytesIO()
        try: 
            fitResult = json_loads(fit_entry.data)
        except Exception as e:
            alert = dmc.Alert(
                f"Failed to parse fit data for DeerLab HDF5 export: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert

        try:
            save(buf, fitResult, format='hdf5')
        except Exception as e:
            alert = dmc.Alert(
                f"DeerLab HDF5 export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert

    
    elif fmt == "hdf5":
        full_name = filename + ext
        buf = io.BytesIO()
        try:
            fitSQL_to_file(buf, fit_entry,dataset_entry, fmt, uncert=True)
        except Exception as e:
            alert = dmc.Alert(
                f"HDF5 export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
    elif fmt == "matlab":
        full_name = filename + ext
        buf = io.BytesIO()
        try:
            fitSQL_to_file(buf, fit_entry,dataset_entry, fmt, uncert=True)
        except Exception as e:
            alert = dmc.Alert(
                f"MATLAB export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert

    elif fmt == "csv":
        buf = io.BytesIO()
        full_name = filename + ".zip" # We will create a zip file containing the CSVs
        try:
            fitSQL_to_file(buf, fit_entry,dataset_entry, fmt, uncert=True)
        except Exception as e:
            print(e)
            traceback.print_tb(e.__traceback__)
            alert = dmc.Alert(
                f"CSV export failed: {str(e)}",
                color="red",
                variant="filled",
            )
            return dash.no_update, True, alert
        

    if _is_pywebview():
        _save_file_native(buf.getvalue(), full_name)
        return dash.no_update, True, dash.no_update
    elif isinstance(buf, io.BytesIO):
        return dcc.send_bytes(buf.getvalue(), full_name), True, dash.no_update
    elif isinstance(buf, io.StringIO):
        return dcc.send_string(buf.getvalue(), full_name), True, dash.no_update
    
    return dash.no_update, False

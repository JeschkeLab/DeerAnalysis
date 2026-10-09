import dash
from dash import html, dcc, callback, Input, Output, State
import base64
import io
import json
from deeranalysis.utils.eprload import bes3t_eprload
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel
import numpy as np
import xarray as xr
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pyepr as pyepr
from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
from deeranalysis.components.data_viewer import data_viewer_layout, plot_upload
from deeranalysis.utils.deerlab_options import experiment_type_options
from deeranalysis.utils.csv_loader import parse_csv_raw, build_csv_store
import deeranalysis.components.dataset_form as df # registers shared MATCH callbacks

dash.register_page(__name__)
page_id = 'upload'

_BRUKER_EXTS = ('.DSC', '.DTA')
_BRUKER_UPLOAD_IDS = {'.DSC': 'upload-bruker-dsc', '.DTA': 'upload-bruker-dta'}


def _bruker_ext(filename):
    """Returns '.DSC' or '.DTA' if the filename is a Bruker BES3T file, otherwise None."""
    ext = '.' + filename.rsplit('.', 1)[-1].upper() if '.' in filename else ''
    return ext if ext in _BRUKER_EXTS else None

layout = html.Div([
    metadata_long_values_model(page_id),
    dcc.Store(id={"type": "metadata-modal-store", "page": page_id}, data=""),
    dcc.Store(id='csv-raw-store'),

    # ---- CSV import modal --------------------------------------------------
    dmc.Modal(
        id='csv-import-modal',
        title=dmc.Title("Import CSV File", order=3),
        size='xl',
        opened=False,
        children=dmc.Stack([
            html.Div(id='csv-preview'),
            dmc.Group([
                dmc.NumberInput(
                    id='csv-skiprows', label='Skip rows', value=0, min=0, step=1, w=140,
                ),
                dmc.Select(
                    id='csv-separator', label='Separator', value=',', w=180,
                    data=[
                        {'label': 'Comma  ( , )', 'value': ','},
                        {'label': 'Semicolon  ( ; )', 'value': ';'},
                        {'label': 'Tab', 'value': '\t'},
                        {'label': 'Space', 'value': ' '},
                    ],
                ),
                dmc.Select(
                    id='csv-time-unit', label='Time unit', value='us', w=140,
                    data=[
                        {'label': 'ns',  'value': 'ns'},
                        {'label': 'µs',  'value': 'us'},
                        {'label': 'ms',  'value': 'ms'},
                        {'label': 's',   'value': 's'},
                    ],
                ),
                dmc.Switch(
                    id='csv-has-header', label='Has header row', checked=True, mt='xl',
                ),
            ]),
            dmc.Group([
                dmc.Select(id='csv-t-col',   label='Time column (t)',         placeholder='Select column…', style={'flex': 1}),
                dmc.Select(id='csv-vre-col', label='Real signal (V_re)',      placeholder='Select column…', style={'flex': 1}),
                dmc.Select(id='csv-vim-col', label='Imaginary signal (V_im)', placeholder='None',           style={'flex': 1}, clearable=True),
            ], grow=True),
            dmc.Group([
                dmc.Button('Cancel', id='csv-cancel-btn', color='gray', variant='subtle'),
                dmc.Button('Import', id='csv-import-btn', color='blue',
                           leftSection=DashIconify(icon='mdi:file-import-outline', width=16)),
            ], justify='flex-end'),
        ], gap='md'),
    ),

    dmc.Title("Import Dataset from File", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dmc.Grid([
        dmc.GridCol([
            dcc.Upload(
                id='upload-data',
                children=dmc.Group([
                    DashIconify(icon="material-symbols:upload-file-outline", width=36, color="var(--mantine-color-blue-6)"),
                    dmc.Stack([
                        dmc.Text("Drag and drop files or click to select", size="sm", fw=500),
                        dmc.Text(".DSC/.DTA, .h5, .csv, .txt, .dat", size="xs", c="dimmed"),
                    ], gap=2),
                ], px="md", py="sm"),
                style={
                    'width': '100%',
                    'borderWidth': '2px',
                    'borderStyle': 'dashed',
                    'borderRadius': 'var(--mantine-radius-sm)',
                    'borderColor': 'var(--mantine-color-blue-3)',
                    'backgroundColor': 'var(--mantine-color-blue-light)',
                    'cursor': 'pointer',
                },
                multiple=True, className="mb-2"
            ),
            dcc.Store(id='bruker-files-store'),
            dmc.Stack(
                id='bruker-files-display',
                gap='sm',
                mb='sm',
                style={'display': 'none'},
                children=[
                    dcc.Upload(id=_BRUKER_UPLOAD_IDS[ext], accept=ext, multiple=False)
                    for ext in _BRUKER_EXTS
                ],
            ),
            dcc.Store(id={'type': 'dataset-store', 'page': page_id}),
            dmc.Autocomplete(id={'type': 'project-name', 'page': page_id}, label="Project Name", mb="sm"),
            dmc.Autocomplete(id={'type': 'sample-name', 'page': page_id}, label="Sample Name", mb="sm"),
            dmc.TextInput(id={'type': 'dataset-name', 'page': page_id}, label="Dataset Name", mb="sm"),

            dmc.Select(
                label='Experiment Type:',
                id={'type': 'experiment-type-dropdown', 'page': page_id},
                value='4pDEER',
                data=experiment_type_options,
            ),

            dmc.Title("Delays", order=4, mt="md", mb="sm"),
            html.Div(id={'type': 'tmin-warning-div', 'page': page_id}),
            dmc.NumberInput(
                id={'type': 'tmin', 'page': page_id},
                label='tmin (ns)',
                allowNegative=True,
                value=0,
                step=4,
                stepHoldDelay=500,
                stepHoldInterval=100,
                decimalScale=2,
                mb="sm",
            ),
            dag.AgGrid(
                id={'type': 'delays-grid', 'page': page_id},
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value (ns)', 'editable': True},
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '200px', 'width': '100%'},
            ),

            dmc.Accordion(
                children=[
                    dmc.AccordionItem(
                        value="parameters",
                        children=[
                            dmc.AccordionControl("Metadata"),
                            dmc.AccordionPanel(
                                children=html.Div(
                                    id={'type': "metadata-content", 'page': page_id},
                                    style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                                )
                            ),
                        ],
                    )
                ],
                mt="md",
            ),
        ], span=4),
        dmc.GridCol([
            data_viewer_layout(page_id=page_id, masking_enabled=True),
            dmc.Button("Add Dataset to Library", id={'type': 'save-dataset-btn', 'page': page_id},
                       color="blue", mb="lg", size="lg"),
        ], span=8),
    ]),
])


def _error_message(message):
    return [dict(
        title='Error',
        message=message,
        icon=DashIconify(icon="material-symbols:warning"),
        color='red',
        duration=4000,
        position="top-center",
    )]


@callback(
    Output({'type': 'dataset-store', 'page': page_id}, 'data'),
    Output({'type': 'metadata-content', 'page': page_id}, 'children'),
    Output({"type": "metadata-modal-store", "page": page_id}, 'data'),
    Output({'type': 'delays-grid', 'page': page_id}, 'rowData'),
    Output({'type': 'dataset-name', 'page': page_id}, 'value'),
    Output({'type': 'tmin', 'page': page_id}, 'value'),
    Output('notification-container', 'sendNotifications'),
    Output('csv-raw-store', 'data'),
    Output('csv-import-modal', 'opened'),
    Output('bruker-files-store', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('bruker-files-store', 'data'),
    prevent_initial_call=True,
)
def handle_file_upload(contents_list, filenames_list, bruker_store):
    """Uploads a dataset and extracts metadata.

    Supported file types: .DSC/.DTA (Bruker BES3T), .h5 (HDF5), .csv
    Bruker files are collected in the bruker-files-store and loaded once both are present.
    """
    no_update_10 = (dash.no_update,) * 10
    if contents_list is None:
        return no_update_10
    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames_list = [filenames_list]

    def _error(message):
        return *no_update_10[:6], _error_message(message), *no_update_10[7:]

    bruker_exts = [_bruker_ext(f) for f in filenames_list]
    if any(bruker_exts):
        if not all(bruker_exts) or len(contents_list) > 2 or len(set(bruker_exts)) != len(bruker_exts):
            return _error("For Bruker BES3T files, upload one .DSC and/or one .DTA file only.")
        # Start a new pair unless the existing store is only half filled
        bruker_store = dict(bruker_store or {})
        if len(bruker_store) == 2 or len(contents_list) == 2:
            bruker_store = {}
        for ext, content, filename in zip(bruker_exts, contents_list, filenames_list):
            bruker_store[ext] = {'content': content, 'filename': filename}
        return *no_update_10[:9], bruker_store

    if len(contents_list) > 1:
        return _error("Please upload only one dataset at a time.")

    filename = filenames_list[0]
    if filename.endswith('.csv') or filename.endswith('.txt') or filename.endswith('.dat'):
        csv_store = {'content': contents_list[0], 'filename': filename}
        return *no_update_10[:7], csv_store, True, None
    elif not filename.endswith('.h5'):
        return _error("Unsupported file type. Please upload .DSC/.DTA (Bruker BES3T), .h5 (HDF5), or .csv files.")

    try:
        decoded = base64.b64decode(contents_list[0].split(',')[1])
        dataarray = pyepr.eprload(io.BytesIO(decoded), type='HDF5')
        metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
        delays = get_delays_dict(dataarray)
        tmin = dataarray.t.values.min() * 1e3
        dataarray.attrs['title'] = filename.split('/')[-1].split('.')[0]
    except Exception as e:
        import traceback
        print(f"Error processing uploaded files: {e}")
        print(traceback.format_exc())
        return _error(f"Error processing files: {str(e)}")

    outputs = _build_dataset_outputs(dataarray, metadata_children, long_values_store, delays, tmin)
    return *outputs, dash.no_update, dash.no_update, None


@callback(
    Output('bruker-files-store', 'data', allow_duplicate=True),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Input(_BRUKER_UPLOAD_IDS['.DSC'], 'contents'),
    Input(_BRUKER_UPLOAD_IDS['.DTA'], 'contents'),
    State(_BRUKER_UPLOAD_IDS['.DSC'], 'filename'),
    State(_BRUKER_UPLOAD_IDS['.DTA'], 'filename'),
    State('bruker-files-store', 'data'),
    prevent_initial_call=True,
)
def handle_bruker_slot_upload(dsc_content, dta_content, dsc_filename, dta_filename, bruker_store):
    """Fills (or replaces) a single .DSC or .DTA slot."""
    if dash.ctx.triggered_id == _BRUKER_UPLOAD_IDS['.DSC']:
        expected, content, filename = '.DSC', dsc_content, dsc_filename
    else:
        expected, content, filename = '.DTA', dta_content, dta_filename
    if content is None:
        return dash.no_update, dash.no_update
    if _bruker_ext(filename) != expected:
        return dash.no_update, _error_message(f"Please select a {expected} file.")
    bruker_store = dict(bruker_store or {})
    bruker_store[expected] = {'content': content, 'filename': filename}
    return bruker_store, dash.no_update


def _bruker_slot(ext, entry):
    """Contents and style of one dashed .DSC/.DTA box."""
    color = 'green' if entry else 'orange'
    style = {
        'borderWidth': '2px',
        'borderStyle': 'dashed',
        'borderRadius': 'var(--mantine-radius-sm)',
        'borderColor': f'var(--mantine-color-{color}-4)',
        'backgroundColor': f'var(--mantine-color-{color}-light)',
        'cursor': 'pointer',
    }
    if entry:
        icon, subtitle = 'material-symbols:check-circle-outline', 'Click or drop to replace'
        # Truncate only the stem so the file ending stays visible
        stem, file_ext = entry['filename'].split('/')[-1].rsplit('.', 1)
        title = dmc.Group([
            dmc.Text(stem, size='sm', fw=500, truncate='end', style={'minWidth': 0}),
            dmc.Text(f".{file_ext}", size='sm', fw=500, style={'flexShrink': 0}),
        ], gap=0, wrap='nowrap')
    else:
        icon, subtitle = 'material-symbols:warning-outline', f"Click or drop to upload the {ext} file"
        title = dmc.Text(f"Missing {ext} file", size='sm', fw=500)
    children = dmc.Group([
        DashIconify(icon=icon, width=24, color=f'var(--mantine-color-{color}-6)'),
        dmc.Stack([
            title,
            dmc.Text(subtitle, size='xs', c='dimmed'),
        ], gap=2, style={'minWidth': 0, 'flex': 1}),
    ], px='sm', py='xs', wrap='nowrap')
    return children, style


@callback(
    Output('bruker-files-display', 'style'),
    Output(_BRUKER_UPLOAD_IDS['.DSC'], 'children'),
    Output(_BRUKER_UPLOAD_IDS['.DSC'], 'style'),
    Output(_BRUKER_UPLOAD_IDS['.DTA'], 'children'),
    Output(_BRUKER_UPLOAD_IDS['.DTA'], 'style'),
    Input('bruker-files-store', 'data'),
)
def render_bruker_slots(bruker_store):
    if not bruker_store:
        return {'display': 'none'}, *(dash.no_update,) * 4
    dsc_children, dsc_style = _bruker_slot('.DSC', bruker_store.get('.DSC'))
    dta_children, dta_style = _bruker_slot('.DTA', bruker_store.get('.DTA'))
    return {}, dsc_children, dsc_style, dta_children, dta_style


@callback(
    Output({'type': 'dataset-store', 'page': page_id}, 'data', allow_duplicate=True),
    Output({'type': 'metadata-content', 'page': page_id}, 'children', allow_duplicate=True),
    Output({"type": "metadata-modal-store", "page": page_id}, 'data', allow_duplicate=True),
    Output({'type': 'delays-grid', 'page': page_id}, 'rowData', allow_duplicate=True),
    Output({'type': 'dataset-name', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'tmin', 'page': page_id}, 'value', allow_duplicate=True),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Input('bruker-files-store', 'data'),
    prevent_initial_call=True,
)
def load_bruker_dataset(bruker_store):
    """Loads the BES3T dataset once both the .DSC and .DTA files are present."""
    if not bruker_store or not all(ext in bruker_store for ext in _BRUKER_EXTS):
        return (dash.no_update,) * 7
    try:
        dsc_decoded = base64.b64decode(bruker_store['.DSC']['content'].split(',')[1])
        dta_decoded = base64.b64decode(bruker_store['.DTA']['content'].split(',')[1])
        dataarray = bes3t_eprload(DSC=dsc_decoded, DTA=dta_decoded)
        metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
        dataarray.attrs.update({'file_format': 'BES3T'})
        dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt', '')))
        delays = get_delays_dict(dataarray)
        tmin = dataarray.attrs.get('deadtime', 0)

        if dataarray.ndim ==2:
            dataarray = dataarray.sum('Y')
    except Exception as e:
        import traceback
        print(f"Error processing uploaded files: {e}")
        print(traceback.format_exc())
        return *(dash.no_update,) * 6, _error_message(f"Error processing files: {str(e)}")

    return _build_dataset_outputs(dataarray, metadata_children, long_values_store, delays, tmin)


def _build_dataset_outputs(dataarray, metadata_children, long_values_store, delays, tmin):
    """Builds the dataset-store and form outputs shared by all loaders."""
    t = dataarray.t.values if 't' in dataarray.coords else dataarray.X.values
    t = t - t[0]

    store_data = {
        'RealData': dataarray.real.values.tolist(),
        'ImagData': dataarray.imag.values.tolist(),
        't': t.tolist(),
        'attrs': dataarray.attrs,
        'delays': delays,
        'tmin': tmin,
        'masked_indices': [],
    }
    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]
    delays_data, store_data = df.check_delays('4pDEER',delays_data,store_data)
    return store_data, metadata_children, long_values_store, delays_data, dataarray.attrs.get('title', ''), tmin, dash.no_update


@callback(
    Output({'type': 'data-viewer-plot', 'page': page_id}, 'figure', allow_duplicate=True),
    Input({'type': 'dataset-store', 'page': page_id}, 'data'),
    Input({'type': 'data-plot-correctphase', 'page': page_id}, 'checked'),
    Input({'type': 'data-masking-enabled', 'page': page_id}, 'checked'),
    prevent_initial_call=True,
)
def _build_signal_figure(dataset_store, correct_phase, masking_enabled):
    if dataset_store is None:
        return dash.no_update
    return plot_upload(dataset_store, correct_phase, masking_enabled)


@callback(
    Output({"type": "metadata-value-modal", 'page': page_id}, "opened"),
    Output({"type": "metadata-value-modal-text", 'page': page_id}, "value"),
    Input({"type": "metadata-show-btn", "key": dash.ALL}, "n_clicks"),
    State({"type": "metadata-modal-store", "page": page_id}, "data"),
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


def get_delays_dict(dataarray: xr.DataArray):
    """Extracts delay parameters from the dataset attributes."""
    delay_keys = ['tau1', 'tau2', 'tau3', 'tau4', 'tau5', 'tau6']
    delays = {}
    for key in delay_keys:
        if key in dataarray.attrs:
            delays[key] = dataarray.attrs[key]
    return delays


# ---------------------------------------------------------------------------
# CSV import modal callbacks
# ---------------------------------------------------------------------------

@callback(
    Output('csv-preview', 'children'),
    Output('csv-t-col',   'data'),
    Output('csv-vre-col', 'data'),
    Output('csv-vim-col', 'data'),
    Input('csv-raw-store',  'data'),
    Input('csv-skiprows',   'value'),
    Input('csv-separator',  'value'),
    Input('csv-has-header', 'checked'),
    prevent_initial_call=True,
)
def update_csv_preview(csv_store, skiprows, separator, has_header):
    if csv_store is None:
        return dash.no_update, [], [], []
    try:
        df = parse_csv_raw(csv_store['content'], skiprows, separator or ',', has_header=bool(has_header))
    except Exception as e:
        return dmc.Alert(f"Could not parse file: {e}", color='red'), [], [], []

    col_options = [{'label': str(c), 'value': str(c)} for c in df.columns]
    preview = dag.AgGrid(
        rowData=df.head(8).astype(str).to_dict('records'),
        columnDefs=[{'field': str(c), 'flex': 1} for c in df.columns],
        className="ag-theme-alpine",
        style={'height': '180px', 'width': '100%'},
        dashGridOptions={'suppressMovableColumns': True},
    )
    return preview, col_options, col_options, col_options


@callback(
    Output('csv-import-modal', 'opened', allow_duplicate=True),
    Output('upload-data', 'contents', allow_duplicate=True),
    Input('csv-cancel-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def cancel_csv_import(_):
    return False, None


@callback(
    Output({'type': 'dataset-store', 'page': page_id}, 'data', allow_duplicate=True),
    Output({'type': 'metadata-content', 'page': page_id}, 'children', allow_duplicate=True),
    Output({"type": "metadata-modal-store", 'page': page_id}, 'data', allow_duplicate=True),
    Output({'type': 'delays-grid', 'page': page_id}, 'rowData', allow_duplicate=True),
    Output({'type': 'dataset-name', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'tmin', 'page': page_id}, 'value', allow_duplicate=True),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Output('csv-import-modal', 'opened', allow_duplicate=True),
    Output('upload-data', 'contents', allow_duplicate=True),
    Input('csv-import-btn', 'n_clicks'),
    State('csv-raw-store',  'data'),
    State('csv-skiprows',   'value'),
    State('csv-separator',  'value'),
    State('csv-t-col',      'value'),
    State('csv-vre-col',    'value'),
    State('csv-vim-col',    'value'),
    State('csv-time-unit',  'value'),
    State('csv-has-header', 'checked'),
    prevent_initial_call=True,
)
def import_csv_data(_, csv_store, skiprows, separator, t_col, vre_col, vim_col, time_unit, has_header):
    no_update_9 = (dash.no_update,) * 9
    if csv_store is None:
        return no_update_9
    if not t_col or not vre_col:
        return *no_update_9[:6], _error_message("Please select at least the Time and Real signal columns."), dash.no_update, dash.no_update
    try:
        df = parse_csv_raw(csv_store['content'], skiprows, separator or ',', has_header=bool(has_header))
    except Exception as e:
        return *no_update_9[:6], _error_message(f"CSV parse error: {e}"), dash.no_update, dash.no_update
    try:
        store_data = build_csv_store(df, t_col, vre_col, vim_col, time_unit)
    except Exception as e:
        return *no_update_9[:6], _error_message(f"Column conversion error: {e}"), dash.no_update, dash.no_update

    title = csv_store['filename'].split('/')[-1].rsplit('.', 1)[0]
    store_data['attrs']['title'] = title
    tmin_ns = store_data['tmin'] * 1e3
    return store_data, None, {}, [], title, tmin_ns, dash.no_update, False, None

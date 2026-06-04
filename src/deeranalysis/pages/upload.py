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
                        dmc.Text(".DSC/.DTA, .h5, .csv, .txt, .dat  —  select both .DSC and .DTA together", size="xs", c="dimmed"),
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
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True,
)
def handle_file_upload(contents_list, filenames_list):
    """Uploads a dataset and extracts metadata.

    Supported file types: .DSC (Bruker BES3T), .h5 (HDF5), .csv
    """
    no_update_9 = (dash.no_update,) * 9
    if contents_list is None:
        return no_update_9
    alert = dash.no_update
    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames_list = [filenames_list]

    if len(contents_list) > 2:
        alert = _error_message("Please upload only one dataset at a time. For Bruker BES3T files, upload both the .DSC and .DTA files together.")
        return *no_update_9[:6], alert, dash.no_update, dash.no_update
    elif len(contents_list) == 2:
        if not (filenames_list[0].endswith('.DSC') and filenames_list[1].endswith('.DTA')) and \
           not (filenames_list[1].endswith('.DSC') and filenames_list[0].endswith('.DTA')):
            alert = _error_message("When uploading two files, please ensure they are the .DSC and .DTA files from Bruker BES3T.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update
        file_format = 'BES3T'
    else:
        if filenames_list[0].endswith('.DSC'):
            alert = _error_message("Please upload both the .DSC and .DTA files from Bruker BES3T together.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update
        elif filenames_list[0].endswith('.h5'):
            file_format = 'hdf5'
        elif filenames_list[0].endswith('.csv') or filenames_list[0].endswith('.txt') or filenames_list[0].endswith('.dat'):
            csv_store = {'content': contents_list[0], 'filename': filenames_list[0]}
            return *no_update_9[:7], csv_store, True
        else:
            alert = _error_message("Unsupported file type. Please upload .DSC/.DTA (Bruker BES3T), .h5 (HDF5), or .csv files.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update

    try:
        if file_format == 'BES3T':
            if filenames_list[0].endswith('.DSC'):
                dsc_content, dta_content = contents_list[0], contents_list[1]
            else:
                dsc_content, dta_content = contents_list[1], contents_list[0]
            dsc_decoded = base64.b64decode(dsc_content.split(',')[1])
            dta_decoded = base64.b64decode(dta_content.split(',')[1])
            dataarray = bes3t_eprload(DSC=dsc_decoded, DTA=dta_decoded)
            metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
            dataarray.attrs.update({'file_format': 'BES3T'})
            dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt', '')))
            delays = get_delays_dict(dataarray)
            tmin = dataarray.attrs.get('deadtime', 0)

            if dataarray.ndim ==2:
                dataarray = dataarray.sum('Y')

        elif file_format == 'hdf5':
            decoded = base64.b64decode(contents_list[0].split(',')[1])
            dataarray = pyepr.eprload(io.BytesIO(decoded), type='HDF5')
            metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
            delays = get_delays_dict(dataarray)
            tmin = dataarray.t.values.min() * 1e3
            dataarray.attrs['title'] = filenames_list[0].split('/')[-1].split('.')[0]

    except Exception as e:
        import traceback
        print(f"Error processing uploaded files: {e}")
        print(traceback.format_exc())
        return *no_update_9[:6], _error_message(f"Error processing files: {str(e)}"), dash.no_update, dash.no_update

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
    return store_data, metadata_children, long_values_store, delays_data, dataarray.attrs.get('title', ''), tmin, alert, dash.no_update, dash.no_update


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

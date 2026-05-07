import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import json
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils.eprload import bes3t_eprload
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel
import numpy as np
import plotly.graph_objs as go
import xarray as xr
import dash_ag_grid as dag  
import dash_mantine_components as dmc
from sqlalchemy.orm import Session
from dash_iconify import DashIconify
import pyepr as pyepr
from deerlab import correctphase
from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
from deeranalysis.components.data_viewer import data_viewer_layout, plot_upload
import datetime as dt
from deeranalysis.utils.deerlab_options import experiment_type_options
from deeranalysis.utils.csv_loader import parse_csv_raw, build_csv_store, TIME_UNIT_TO_US

dash.register_page(__name__)
page_id = 'upload'

layout = html.Div([
    metadata_long_values_model(page_id),
    dcc.Store(id={"type":"metadata-modal-store","page":page_id}, data=""),
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
                dmc.Select(id='csv-t-col',   label='Time column (t)',                placeholder='Select column…', style={'flex': 1}),
                dmc.Select(id='csv-vre-col', label='Real signal (V_re)',             placeholder='Select column…', style={'flex': 1}),
                dmc.Select(id='csv-vim-col', label='Imaginary signal (V_im)',        placeholder='None',           style={'flex': 1}, clearable=True),
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
                        dmc.Text(".DSC/.DTA, .h5, .csv  —  select both .DSC and .DTA together", size="xs", c="dimmed"),
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
            dcc.Store(id={'type':"dataset-store",'page': page_id}),
            dmc.Autocomplete(id="project-name", label="Project Name", mb="sm"),
            dmc.Autocomplete(id="sample-name", label="Sample Name", mb="sm"),
            dmc.TextInput(id="dataset-name", label="Dataset Name", mb="sm"),
            
            dmc.Select(
                label='Experiment Type:',
                id='experiment-type-dropdown',
                value='4pDEER',
                data=experiment_type_options
            ),
            
            dmc.Title("Delays", order=4, mt="md", mb="sm"),
            html.Div(id='tmin-warning-div'),
            dmc.NumberInput(
                id={"type": "tmin", 'page': page_id},
                label='tmin (ns)',
                allowNegative=True,
                value=0,
                step=4,
                stepHoldDelay=500,
                stepHoldInterval=100,
                decimalScale=2,
                mb="sm"
            ),
            dag.AgGrid(
                id='delays-grid',
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value (ns)', 'editable': True}
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '200px', 'width': '100%'}
            ),
            
            dmc.Accordion(
                children=[
                    dmc.AccordionItem(
                        value="parameters",
                        children=[
                            dmc.AccordionControl("Metadata"),
                            dmc.AccordionPanel(
                                children=html.Div(
                                id={'type':"metadata-content", 'page': page_id},
                                style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},)
                            )
                        ]
                    )
                ],
                mt="md"
            )
        ], span=4),
        dmc.GridCol([
            data_viewer_layout(page_id=page_id,masking_enabled=True),
            dmc.Button("Add Dataset to Libary", id="save-dataset-btn", color="blue", mb="lg",size="lg"),
        ], span=8),
    ]),
])


def _error_message(message):
    return [dict(
        title='Error',
        message= message,
        icon= DashIconify(icon="material-symbols:warning"),
        color= 'red',
        duration= 4000,
        position = "top-center",
    )]

@callback(
    Output({'type':"dataset-store",'page': page_id}, 'data'),
    Output({'type':"metadata-content", 'page': page_id}, 'children'),
    Output({"type":"metadata-modal-store","page":page_id}, 'data'),
    Output('delays-grid', 'rowData'),
    Output('dataset-name', 'value'),
    Output({"type": "tmin", 'page': page_id}, 'value'),
    Output('notification-container', 'sendNotifications'),
    Output('csv-raw-store', 'data'),
    Output('csv-import-modal', 'opened'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True)
def handle_file_upload(contents_list, filenames_list):
    """ Uploads a dataset and extracts metadata

    Suported file types: .DSC (Bruker BES3t), 'h5' (HDF5), '.csv' (Comma-separated values)
    """

    no_update_9 = (dash.no_update,) * 9
    if contents_list is None:
        return no_update_9
    alert = dash.no_update
    # Ensure we're working with lists
    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames_list = [filenames_list]

    # Only permit multiple files for .DSC + .DTA
    if len(contents_list) > 2:
        alert = _error_message("Please upload only one dataset at a time. For Bruker BES3T files, upload both the .DSC and .DTA files together.")
        return *no_update_9[:6], alert, dash.no_update, dash.no_update
    elif len(contents_list) == 2:
        if not (filenames_list[0].endswith('.DSC') and filenames_list[1].endswith('.DTA')) and not (filenames_list[1].endswith('.DSC') and filenames_list[0].endswith('.DTA')):
            alert = _error_message("When uploading two files, please ensure they are the .DSC and .DTA files from Bruker BES3T.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update
        file_format= 'BES3T'
    else:
        if filenames_list[0].endswith('.DSC'):
            alert = _error_message("Please upload both the .DSC and .DTA files from Bruker BES3T together.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update
        elif filenames_list[0].endswith('.h5'):
            file_format = 'hdf5'
        elif filenames_list[0].endswith('.csv'):
            # Hand off to the CSV import modal
            csv_store = {'content': contents_list[0], 'filename': filenames_list[0]}
            return *no_update_9[:7], csv_store, True
        else:
            alert = _error_message("Unsupported file type. Please upload .DSC/.DTA (Bruker BES3T), .h5 (HDF5), or .csv files.")
            return *no_update_9[:6], alert, dash.no_update, dash.no_update

    try:
        if file_format == 'BES3T':
            # Identify which content is which
            if filenames_list[0].endswith('.DSC'):
                dsc_content = contents_list[0]
                dta_content = contents_list[1]
            else:
                dsc_content = contents_list[1]
                dta_content = contents_list[0]

            # Decode and parse the files
            dsc_decoded = base64.b64decode(dsc_content.split(',')[1])
            dta_decoded = base64.b64decode(dta_content.split(',')[1])
            dataarray = bes3t_eprload(DSC=dsc_decoded,DTA=dta_decoded)

            metadata_children, long_values_store = build_metadata_section_datarray(dataarray)

            # Extract delays from pulsespel
            dataarray.attrs.update({'file_format': 'BES3T'})
            dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt','')))

            delays = get_delays_dict(dataarray)
            tmin = dataarray.attrs.get('deadtime', 0)

        elif file_format == 'hdf5':
            decoded = base64.b64decode(contents_list[0].split(',')[1])
            dataarray = pyepr.eprload(io.BytesIO(decoded),type='HDF5')
            metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
            delays = get_delays_dict(dataarray)
            tmin = dataarray.t.values.min()*1e3 # Convert from microseconds to nanoseconds
            
            filename = filenames_list[0].split('/')[-1].split('.')[0]
            dataarray.attrs['title'] = filename

    except Exception as e:
        alert = _error_message(f"Error processing files: {str(e)}")
        import traceback
        print(f"Error processing uploaded files: {e}")
        print(traceback.format_exc())
        return *no_update_9[:6], alert, dash.no_update, dash.no_update
    
    
    # save dataarray to dcc.Store for later use
    t = dataarray.t.values if 't' in dataarray.coords else dataarray.X.values
    t = t - t[0]  # Ensure time starts at zero


    store_data = {}
    store_data['RealData'] = dataarray.real.values.tolist()
    store_data['ImagData'] = dataarray.imag.values.tolist()
    store_data['t'] = t.tolist()
    store_data['attrs'] = dataarray.attrs
    store_data['delays'] = delays
    store_data['tmin'] = tmin
    store_data['masked_indices'] = []


    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]
    
    return store_data, metadata_children, long_values_store, delays_data, dataarray.attrs.get('title', ''), tmin, alert, dash.no_update, dash.no_update


@callback(
    Output({'type':'data-viewer-plot','page': page_id}, 'figure', allow_duplicate=True),
    Input({'type':"dataset-store",'page': page_id}, 'data'),
    Input({'type':'data-plot-correctphase','page': page_id}, 'checked'),
    Input({'type':'data-masking-enabled','page': page_id}, 'checked'),
    prevent_initial_call=True
)
def _build_signal_figure(dataset_store, correct_phase, masking_enabled):
    """Rebuilds the signal figure whenever the dataset or phase switch changes."""
    if dataset_store is None:
        return dash.no_update

    figure = plot_upload(dataset_store, correct_phase, masking_enabled)
    return figure

@callback(
    Output({"type": "metadata-value-modal",'page': page_id}, "opened"),
    Output({"type":"metadata-value-modal-text",'page': page_id}, "value"),
    Input({"type": "metadata-show-btn", "key": dash.ALL}, "n_clicks"),
    State({"type":"metadata-modal-store","page":page_id}, "data"),
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
        Output('notification-container', 'sendNotifications', allow_duplicate=True),
        Output('project-name', 'value'),
        Output('sample-name', 'value'),
        Output('dataset-name', 'value', allow_duplicate=True),
        Output({'type':"dataset-store",'page': page_id}, 'data', allow_duplicate=True),
        Output('delays-grid', 'rowData', allow_duplicate=True),
        Output({'type':'data-viewer-plot','page': page_id}, 'figure', allow_duplicate=True),
        Output({"type": "tmin", 'page': page_id}, 'value', allow_duplicate=True),
        Output({'type': "metadata-content", 'page': page_id}, 'children', allow_duplicate=True),
        Output({"type": "metadata-modal-store", "page": page_id}, 'data', allow_duplicate=True),
        Input('save-dataset-btn', 'n_clicks'),
        State('project-name', 'value'),
        State('sample-name', 'value'),
        State('dataset-name', 'value'),
        State({'type':"dataset-store",'page': page_id}, 'data'),
        State('experiment-type-dropdown', 'value'),
        prevent_initial_call=True)
def save_dataset(n_clicks, project_name, sample_name, dataset_name, dataset_store, experiment_type,
                 phase_correction=True):
    """ Saves the uploaded dataset to the database """
    no_update_10 = (dash.no_update,) * 10
    if n_clicks is None:
        return no_update_10
    if not project_name or not sample_name or not dataset_name:
        notification = [dict(
            title='Missing Information',
            message='Please fill in all required fields (Project, Sample, and Dataset names)',
            icon=DashIconify(icon="mdi:alert-circle-outline",height=50),
            color='yellow',
            duration=4000,
            position = "top-center",
        )]
        return notification, *no_update_10[1:]
    
    if dataset_store is None:
        notification = [dict(
            title='No Dataset',
            message='No dataset uploaded. Please upload a dataset first.',
            icon=DashIconify(icon="mdi:alert-circle-outline",height=50),
            color='yellow',
            duration=4000,
            position = "top-center"
        )]
        return notification, *no_update_10[1:]
        
    session = get_session()
    if session is None:
        notification = [dict(
            title='Database Error',
            message='Could not connect to the database.',
            icon=DashIconify(icon="material-symbols:warning"),
            color='red',
            duration=4000,
            position = "top-center",
        )]
        return notification, *no_update_10[1:]
    
    delays = dataset_store.get('delays', {})

    t = np.array(dataset_store['t'])
    t = t - t[0]
    tmin = dataset_store.get('tmin', 0) # ns
    print(f"Saving dataset with tmin={tmin} microseconds and delays={delays}")
    t = t + tmin

    V_real = np.array(dataset_store['RealData'])
    V_imag = np.array(dataset_store['ImagData'])
    if phase_correction:
        V = V_real + 1j * V_imag
        V_real, V_imag,_ = correctphase(V, full_output=True)
        
    masked_indices = dataset_store.get('masked_indices', []) or []
    mask = np.ones(len(t), dtype=bool)
    if masked_indices:
        mask[np.array(masked_indices, dtype=int)] = False
    mask = mask.tolist()

    datetime_str = dataset_store['attrs'].get('datetime', None)
    if datetime_str:
        datetime = dt.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
    else:
        datetime = None

    new_dataset = Dataset(
        name=dataset_name,
        project=project_name,
        sample=sample_name,
        t=t.tolist(),
        V=V_real.tolist(),
        V_im=V_imag.tolist(),
        mask=mask,
        exp=experiment_type,
        delays=delays,
        meta=dataset_store['attrs'],
        measured_at=datetime
    )
    session.add(new_dataset)
    session.commit()
    session.close()
    
    notification = [dict(
        title='Success',
        message=f"Dataset '{dataset_name}' successfully saved to project '{project_name}'!",
        icon=DashIconify(icon="material-symbols:check-circle"),
        color='green',
        duration=4000,
    )]
    
    # Clear all fields
    empty_figure = go.Figure()
    empty_figure.update_layout(
        title='Upload a dataset to view',
        xaxis_title='Time (us)',
        yaxis_title='Signal (a.u.)',
    )
    
    return notification, '', '', '', None, [], empty_figure, 0, None, {}


@callback(
    Output({'type':"dataset-store",'page': page_id}, 'data', allow_duplicate=True),
    Input({"type": "tmin", 'page': page_id}, 'value'),
    State({'type':"dataset-store",'page': page_id}, 'data'),
    prevent_initial_call=True
)
def update_tmin(tmin, dataset_store):
    """ Updates the tmin value in the dataset store when the shift input is changed """
    if dataset_store is None:
        return dash.no_update

    dataset_store['tmin'] = tmin / 1e3
    return dataset_store


@callback(
    Output('project-name', 'data'),
    Output('sample-name', 'data'),
    Input('project-name', 'n_clicks'),
    prevent_initial_call=False)
def update_samples_and_projects(n_clicks):
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()
    
    projects = list(set(ds.project for ds in datasets))
    samples = list(set(ds.sample for ds in datasets))
    return projects, samples


@callback(
    Output('delays-grid', 'rowData',allow_duplicate=True),
    Input('experiment-type-dropdown', 'value'),
    State('delays-grid', 'rowData'),
    
    prevent_initial_call=True
)
def check_delays(exp_type,delays_row_data,):
    """ Checks that enough delay parameters are present for the selected experiment type.
    """
    def get_delays_by_value(options_list, value):
        """Extract the delays element from a list of dicts based on a value."""
        option = next((opt for opt in options_list if opt.get('value') == value), None)
        return option.get('delays') if option else None
    
    required_delays = get_delays_by_value(experiment_type_options, exp_type)

    delays = {row['parameter']: row['value'] for row in delays_row_data}
    print(f"Checking delays for experiment type {exp_type} with current delays: {delays}")
    missing_delays = []
    new_delays = delays.copy()
    for delay in required_delays:
        if delay not in delays:
            new_delays[delay] = 0
            missing_delays.append(delay)

    new_delays_row_data = [{'parameter': k, 'value': v} for k, v in new_delays.items()]
    return new_delays_row_data

@callback(
    Output('tmin-warning-div', 'children'),
    Input({'type':"dataset-store",'page': page_id}, 'data'),
    Input('experiment-type-dropdown', 'value'),
    prevent_initial_call=True
)
def check_tmin(store, exp_type):
    """ Checks that the data maxmium is close to predicted value based on delays, and raises a warning if not"""
    
    if store is None:
        return None
    delays = store.get('delays', {})
    
    if exp_type == '4pDEER':
        peak_time = delays.get('tau1',0)/1e3
    elif exp_type == '5pDEER':
        peak_time = delays.get('tau3',0)/1e3
    elif exp_type == 'RIDME':
        peak_time = delays.get('tau1',0)/1e3
    else:
        return None  # No specific requirements for unknown experiment types

    t_min = store.get('tmin', 0) # already in microseconds
    t = np.array(store['t']) + t_min
    data_max_time = t[np.argmax(np.abs(store['RealData']))]
    threshold = 50/1e3 # 50 ns in microseconds

    if abs(peak_time - data_max_time) > threshold:
        return dmc.Alert(
            title="Warning: tmin may be incorrect",
            children=f"The expected peak time based on delays is {peak_time*1e3:.0f} ns, but the data maximum is at {data_max_time*1e3:.0f} ns. Please check that tmin is set correctly.",
            color="yellow",
            mb="md",
        )
    return None

def get_delays_dict(dataarray: xr.DataArray):
    """ Extracts delay parameters from the dataset attributes """
    # Possible delay keys in the attributes
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
    Input('csv-raw-store',   'data'),
    Input('csv-skiprows',    'value'),
    Input('csv-separator',   'value'),
    Input('csv-has-header',  'checked'),
    prevent_initial_call=True,
)
def update_csv_preview(csv_store, skiprows, separator, has_header):
    """ Re-parses CSV and updates the preview table and column selectors """
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
    Output({'type':"dataset-store",'page': page_id}, 'data', allow_duplicate=True),
    Output({'type': "metadata-content",    'page': page_id}, 'children', allow_duplicate=True),
    Output({"type": "metadata-modal-store",'page': page_id}, 'data',     allow_duplicate=True),
    Output('delays-grid', 'rowData', allow_duplicate=True),
    Output('dataset-name', 'value',  allow_duplicate=True),
    Output({"type": "tmin", 'page': page_id}, 'value', allow_duplicate=True),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Output('csv-import-modal', 'opened', allow_duplicate=True),
    Output('upload-data', 'contents', allow_duplicate=True),
    Input('csv-import-btn', 'n_clicks'),
    State('csv-raw-store',   'data'),
    State('csv-skiprows',    'value'),
    State('csv-separator',   'value'),
    State('csv-t-col',       'value'),
    State('csv-vre-col',     'value'),
    State('csv-vim-col',     'value'),
    State('csv-time-unit',   'value'),
    State('csv-has-header',  'checked'),
    prevent_initial_call=True,
)
def import_csv_data(_, csv_store, skiprows, separator, t_col, vre_col, vim_col, time_unit, has_header):
    no_update_9 = (dash.no_update,) * 9

    if csv_store is None:
        return no_update_9

    if not t_col or not vre_col:
        alert = _error_message("Please select at least the Time and Real signal columns.")
        return *no_update_9[:6], alert, dash.no_update, dash.no_update

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

    tmin_ns = store_data['tmin'] * 1e3  # shown in ns in the UI

    return store_data, None, {}, [], title, tmin_ns, dash.no_update, False, None


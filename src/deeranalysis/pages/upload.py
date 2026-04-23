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

from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
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

    dmc.Title("Upload Dataset from File", order=1, mb="md"),
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
            dcc.Store(id='dataset-store'),
            dmc.Autocomplete(id="project-name", label="Project Name", mb="sm"),
            dmc.Autocomplete(id="sample-name", label="Sample Name", mb="sm"),
            dmc.TextInput(id="dataset-name", label="Dataset Name", mb="sm"),
            
            dmc.Select(
                label='Experiment Type:',
                id='experiment-type-dropdown',
                value='4pDEER',
                data=[{'label': '3-pulse', 'value': '3pDEER'},
                        {'label': '4-pulse', 'value': '4pDEER'},
                        {'label': '5-pulse', 'value': '5pDEER'},
                        {'label': 'RIDME', 'value': '5pRIDME'},]
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
            dmc.Title("Data Viewer", order=2, mb="sm"),
            dcc.Graph(id='data-viewer-plot',
                      style={'height': '500px'}),
            dmc.Group([
                dmc.Text("Box/lasso select points, then:", size="sm", c="dimmed"),
                dmc.Button(
                    "Mask Selected",
                    id="mask-selected-btn",
                    color="orange",
                    size="sm",
                    variant="light",
                    leftSection=DashIconify(icon="mdi:eye-off-outline", width=16),
                ),
                dmc.Button(
                    "Clear Masks",
                    id="clear-masks-btn",
                    color="gray",
                    size="sm",
                    variant="subtle",
                ),
                dmc.Badge(id="masked-count-badge", color="orange", variant="light", size="sm"),
            ], mt="xs", mb="md"),
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
    Output('dataset-store', 'data'),
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
            return *no_update_9[:7], contents_list[0], True
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

    except Exception as e:
        alert = _error_message(f"Error processing files: {str(e)}")
        import traceback
        print(f"Error processing uploaded files: {e}")
        print(traceback.format_exc())
        return *no_update_9[:6], alert, dash.no_update, dash.no_update
    
    
    # save dataarray to dcc.Store for later use
    store_data = {}
    store_data['RealData'] = dataarray.real.values.tolist()
    store_data['ImagData'] = dataarray.imag.values.tolist()
    store_data['t'] = dataarray.t.values.tolist() if hasattr(dataarray, 't') else dataarray.X.values.tolist()
    store_data['attrs'] = dataarray.attrs
    store_data['delays'] = delays
    store_data['tmin'] = tmin
    store_data['masked_indices'] = []


    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]
    
    return store_data, metadata_children, long_values_store, delays_data, dataarray.attrs.get('title', ''), tmin, alert, dash.no_update, dash.no_update


@callback(
    Output('data-viewer-plot', 'figure', allow_duplicate=True),
    Input('dataset-store', 'data'),
    prevent_initial_call=True
)
def _build_signal_figure(dataset_store):
    """ Updates the plot when tmin is changed """
    if dataset_store is None:
        return dash.no_update

    t_min = dataset_store.get('tmin', 0)
    t = np.array(dataset_store['t']) + t_min
    V = np.array(dataset_store['RealData']) + 1j * np.array(dataset_store['ImagData'])
    V = V / np.max(np.abs(V))
    masked_indices = np.array(dataset_store.get('masked_indices', []), dtype=int)

    title_text = dataset_store['attrs'].get('title', 'Uploaded Data')

    traces = [
        # Invisible markers on Real trace so box/lasso select captures points
        go.Scatter(
            x=t, y=V.real,
            mode='lines+markers',
            name='Real',
            marker=dict(size=8, opacity=0),
        ),
        go.Scatter(x=t, y=V.imag, mode='lines', name='Imag'),
    ]

    if len(masked_indices) > 0:
        traces.append(go.Scatter(
            x=t[masked_indices],
            y=V.real[masked_indices],
            mode='markers',
            name='Masked (Real)',
            marker=dict(size=8, color='rgba(180, 180, 180, 0.4)'),
            hovertemplate='<b>Masked (Real)</b><br>t=%{x:.3f}<br>V=%{y:.4f}<extra></extra>',
        ))
        traces.append(go.Scatter(
            x=t[masked_indices],
            y=V.imag[masked_indices],
            mode='markers',
            name='Masked (Imag)',
            marker=dict(size=8, color='rgba(180, 180, 180, 0.4)'),
            hovertemplate='<b>Masked (Imag)</b><br>t=%{x:.3f}<br>V=%{y:.4f}<extra></extra>',
        ))

    figure = {
        'data': traces,
        'layout': go.Layout(
            title=title_text,
            xaxis_title='Time (us)',
            yaxis_title='Signal (a.u.)',
            template=None,
            dragmode='select',
            clickmode='event+select',
        )
    }
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
    Output('dataset-store', 'data', allow_duplicate=True),
    Input('mask-selected-btn', 'n_clicks'),
    State('data-viewer-plot', 'selectedData'),
    State('dataset-store', 'data'),
    prevent_initial_call=True,
)
def mask_selected_points(n_clicks, selected_data, dataset_store):
    """ Adds box/lasso-selected points to the masked set """
    if dataset_store is None or not selected_data:
        return dash.no_update

    current_masked = set(dataset_store.get('masked_indices', []))
    for point in selected_data.get('points', []):
        # curveNumber 0 is the Real trace (with invisible markers)
        if point.get('curveNumber') == 0:
            current_masked.add(point['pointIndex'])

    dataset_store['masked_indices'] = sorted(current_masked)
    return dataset_store


@callback(
    Output('dataset-store', 'data', allow_duplicate=True),
    Input('clear-masks-btn', 'n_clicks'),
    State('dataset-store', 'data'),
    prevent_initial_call=True,
)
def clear_masks(n_clicks, dataset_store):
    """ Removes all masked points """
    if dataset_store is None:
        return dash.no_update
    dataset_store['masked_indices'] = []
    return dataset_store


@callback(
    Output('masked-count-badge', 'children'),
    Input('dataset-store', 'data'),
)
def update_masked_badge(dataset_store):
    if dataset_store is None:
        return ""
    count = len(dataset_store.get('masked_indices', []))
    return f"{count} masked" if count > 0 else ""


@callback(
        Output('notification-container', 'sendNotifications', allow_duplicate=True),
        Output('project-name', 'value'),
        Output('sample-name', 'value'),
        Output('dataset-name', 'value', allow_duplicate=True),
        Output('dataset-store', 'data', allow_duplicate=True),
        Output('delays-grid', 'rowData', allow_duplicate=True),
        Output('data-viewer-plot', 'figure', allow_duplicate=True),
        Output({"type": "tmin", 'page': page_id}, 'value', allow_duplicate=True),
        Output({'type': "metadata-content", 'page': page_id}, 'children', allow_duplicate=True),
        Output({"type": "metadata-modal-store", "page": page_id}, 'data', allow_duplicate=True),
        Input('save-dataset-btn', 'n_clicks'),
        State('project-name', 'value'),
        State('sample-name', 'value'),
        State('dataset-name', 'value'),
        State('dataset-store', 'data'),
        State('experiment-type-dropdown', 'value'),
        prevent_initial_call=True)
def save_dataset(n_clicks, project_name, sample_name, dataset_name, dataset_store, experiment_type):
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

    masked_indices = dataset_store.get('masked_indices', []) or []
    mask = np.ones(len(t), dtype=bool)
    if masked_indices:
        mask[np.array(masked_indices, dtype=int)] = False
    mask = mask.tolist()

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
        meta=dataset_store['attrs']
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
    Output('dataset-store', 'data', allow_duplicate=True),
    Input({"type": "tmin", 'page': page_id}, 'value'),
    State('dataset-store', 'data'),
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

    if exp_type == '4pDEER':
        required_delays = ['tau1', 'tau2', ]
    elif exp_type == '5pDEER':
        required_delays = ['tau1', 'tau2', 'tau3']
    elif exp_type == '3pDEER':
        required_delays = ['tau1', ]
    elif exp_type == 'RIDME':
        required_delays = ['tau1', 'tau2', ]
    else:
        print(f"Unknown experiment type: {exp_type}. No specific delay requirements applied.")
        return True, []  # No specific requirements for unknown experiment types

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
    Input('dataset-store', 'data'),
    State('experiment-type-dropdown', 'value'),
    prevent_initial_call=True
)
def check_tmin(store,exp_type):
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

def _parse_csv_raw(raw_content, skiprows, separator):
    """ Decode base64 CSV content and return a DataFrame """
    decoded = base64.b64decode(raw_content.split(',')[1])
    text = decoded.decode('utf-8', errors='replace')
    return pd.read_csv(io.StringIO(text), skiprows=int(skiprows or 0), sep=separator)


@callback(
    Output('csv-preview', 'children'),
    Output('csv-t-col',   'data'),
    Output('csv-vre-col', 'data'),
    Output('csv-vim-col', 'data'),
    Input('csv-raw-store',  'data'),
    Input('csv-skiprows',   'value'),
    Input('csv-separator',  'value'),
    prevent_initial_call=True,
)
def update_csv_preview(raw_content, skiprows, separator):
    """ Re-parses CSV and updates the preview table and column selectors """
    if raw_content is None:
        return dash.no_update, [], [], []

    try:
        df = _parse_csv_raw(raw_content, skiprows, separator or ',')
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
    Input('csv-cancel-btn', 'n_clicks'),
    prevent_initial_call=True,
)
def cancel_csv_import(_):
    return False


_TIME_UNIT_TO_US = {'ns': 1e-3, 'us': 1.0, 'ms': 1e3, 's': 1e6}

@callback(
    Output('dataset-store', 'data', allow_duplicate=True),
    Output({'type': "metadata-content",    'page': page_id}, 'children', allow_duplicate=True),
    Output({"type": "metadata-modal-store",'page': page_id}, 'data',     allow_duplicate=True),
    Output('delays-grid', 'rowData', allow_duplicate=True),
    Output('dataset-name', 'value',  allow_duplicate=True),
    Output({"type": "tmin", 'page': page_id}, 'value', allow_duplicate=True),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Output('csv-import-modal', 'opened', allow_duplicate=True),
    Input('csv-import-btn', 'n_clicks'),
    State('csv-raw-store',  'data'),
    State('csv-skiprows',   'value'),
    State('csv-separator',  'value'),
    State('csv-t-col',      'value'),
    State('csv-vre-col',    'value'),
    State('csv-vim-col',    'value'),
    State('csv-time-unit',  'value'),
    prevent_initial_call=True,
)
def import_csv_data(_, raw_content, skiprows, separator, t_col, vre_col, vim_col, time_unit):
    no_update_8 = (dash.no_update,) * 8

    if raw_content is None:
        return no_update_8

    if not t_col or not vre_col:
        alert = _error_message("Please select at least the Time and Real signal columns.")
        return *no_update_8[:6], alert, dash.no_update

    try:
        df = _parse_csv_raw(raw_content, skiprows, separator or ',')
    except Exception as e:
        return *no_update_8[:6], _error_message(f"CSV parse error: {e}"), dash.no_update

    try:
        scale = _TIME_UNIT_TO_US.get(time_unit or 'us', 1.0)
        t_us  = pd.to_numeric(df[t_col],   errors='raise').to_numpy() * scale
        V_re  = pd.to_numeric(df[vre_col], errors='raise').to_numpy()
        V_im  = pd.to_numeric(df[vim_col], errors='raise').to_numpy() if vim_col else np.zeros_like(V_re)
    except Exception as e:
        return *no_update_8[:6], _error_message(f"Column conversion error: {e}"), dash.no_update

    tmin_ns = float(t_us[0]) * 1e3   # first point = deadtime, shown in ns in the UI
    t_rel   = t_us - t_us[0]         # zero-based time for the store

    store_data = {
        'RealData':       V_re.tolist(),
        'ImagData':       V_im.tolist(),
        't':              t_rel.tolist(),
        'attrs':          {'title': 'Imported CSV', 'file_format': 'csv'},
        'delays':         {},
        'tmin':           float(t_us[0]),
        'masked_indices': [],
    }

    return store_data, None, {}, [], '', tmin_ns, dash.no_update, False


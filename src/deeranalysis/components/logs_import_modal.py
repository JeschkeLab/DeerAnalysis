import dash
from dash import html, dcc, callback, Input, Output, State
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel
from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
from deeranalysis.utils.deerlab_options import experiment_type_options
import dash_ag_grid as dag
import numpy as np
import plotly.graph_objs as go
import json

page_id = 'logs-import'
prefix = 'logs-import-'


def create_logs_import_modal(id="logs-import-modal", title="Import from LOGs"):
    return dmc.Modal(
        title=title,
        id=id,
        size="80%",
        opened=False,
        children=[
            metadata_long_values_model(page_id),
            dcc.Store(id={"type": "metadata-modal-store", "page": page_id}, data=""),
            dcc.Store(id=prefix + 'dataset-store'),
            dmc.Grid([
                dmc.GridCol([
                    dmc.Autocomplete(id=prefix + "project-name", label="Project Name", mb="sm"),
                    dmc.Autocomplete(id=prefix + "sample-name", label="Sample Name", mb="sm"),
                    dmc.TextInput(id=prefix + "dataset-name", label="Dataset Name", mb="sm"),
                    dmc.Select(
                        label='Experiment Type:',
                        id=prefix + 'experiment-type-dropdown',
                        value='4pDEER',
                        data=[
                            {'label': '3-pulse', 'value': '3pDEER'},
                            {'label': '4-pulse', 'value': '4pDEER'},
                            {'label': '5-pulse', 'value': '5pDEER'},
                            {'label': 'RIDME', 'value': '5pRIDME'},
                        ]
                    ),
                    dmc.Title("Delays", order=4, mt="md", mb="sm"),
                    html.Div(id=prefix + 'tmin-warning-div'),
                    dmc.NumberInput(
                        id={"type": "tmin-shift", 'page': page_id},
                        label='Shift tmin (ns)',
                        allowNegative=True,
                        value=0,
                        step=4,
                        stepHoldDelay=500,
                        stepHoldInterval=100,
                        decimalScale=2,
                        mb="sm"
                    ),
                    dag.AgGrid(
                        id=prefix + 'delays-grid',
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
                                            id={'type': "metadata-content", 'page': page_id},
                                            style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                                        )
                                    )
                                ]
                            )
                        ],
                        mt="md"
                    )
                ], span=4),
                dmc.GridCol([
                    dmc.Title("Data Viewer", order=4, mb="sm"),
                    dcc.Graph(
                        id=prefix + 'preview-graph',
                        style={'height': '500px'}
                    ),
                    dmc.Button("Add Dataset", id=prefix + "save-dataset-btn", color="blue", mb="md"),
                ], span=8),
            ]),
        ],
        overlayProps={"color": "black", "opacity": 0.5, "blur": 0.5},
    )


def _error_notification(message):
    return [dict(
        title='Error',
        message=message,
        icon=DashIconify(icon="material-symbols:warning"),
        color='red',
        duration=4000
    )]


def get_delays_dict(dataarray):
    delay_keys = ['tau1', 'tau2', 'tau3', 'tau4', 'tau5', 'tau6']
    delays = {}
    for key in delay_keys:
        if key in dataarray.attrs:
            delays[key] = dataarray.attrs[key]
    return delays


def build_store_data(dataarray):
    """Build the dataset store dict from an xarray DataArray."""
    dataarray.attrs.update({'file_format': 'BES3T'})
    dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt', '')))

    delays = get_delays_dict(dataarray)
    tmin = delays.get('deadtime', 0)

    store_data = {
        'RealData': dataarray.real.values.tolist(),
        'ImagData': dataarray.imag.values.tolist(),
        't': dataarray.X.values.tolist(),
        'attrs': dataarray.attrs,
        'delays': delays,
        'tmin': delays.get('deadtime', 0),
    }
    metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]

    return store_data, metadata_children, long_values_store, delays_data, tmin


# --- Callbacks ---

@callback(
    Output(prefix + 'preview-graph', 'figure', allow_duplicate=True),
    Input(prefix + 'dataset-store', 'data'),
    prevent_initial_call=True
)
def _build_signal_figure(dataset_store):
    if dataset_store is None:
        return dash.no_update

    t_min = dataset_store.get('tmin', 0)
    t = np.array(dataset_store['t']) + t_min
    V = np.array(dataset_store['RealData']) + 1j * np.array(dataset_store['ImagData'])
    V = V / np.max(np.abs(V))

    title_text = dataset_store['attrs'].get('title', 'LOGs Data')

    return {
        'data': [
            go.Scatter(x=t, y=V.real, mode='lines', name='Real'),
            go.Scatter(x=t, y=V.imag, mode='lines', name='Imag'),
        ],
        'layout': go.Layout(
            title=title_text,
            xaxis_title='Time (us)',
            yaxis_title='Signal (a.u.)',
        )
    }


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


@callback(
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Output(prefix + 'project-name', 'value', allow_duplicate=True),
    Output(prefix + 'sample-name', 'value', allow_duplicate=True),
    Output(prefix + 'dataset-name', 'value', allow_duplicate=True),
    Output(prefix + 'dataset-store', 'data', allow_duplicate=True),
    Output(prefix + 'delays-grid', 'rowData', allow_duplicate=True),
    Output(prefix + 'preview-graph', 'figure', allow_duplicate=True),
    Output({"type": "tmin-shift", 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': "metadata-content", 'page': page_id}, 'children', allow_duplicate=True),
    Output({"type": "metadata-modal-store", "page": page_id}, 'data', allow_duplicate=True),
    Input(prefix + 'save-dataset-btn', 'n_clicks'),
    State(prefix + 'project-name', 'value'),
    State(prefix + 'sample-name', 'value'),
    State(prefix + 'dataset-name', 'value'),
    State(prefix + 'dataset-store', 'data'),
    State(prefix + 'experiment-type-dropdown', 'value'),
    prevent_initial_call=True
)
def save_dataset(n_clicks, project_name, sample_name, dataset_name, dataset_store, experiment_type):
    no_update_10 = (dash.no_update,) * 10
    if n_clicks is None:
        return no_update_10
    if not project_name or not sample_name or not dataset_name:
        notification = [dict(
            title='Missing Information',
            message='Please fill in all required fields (Project, Sample, and Dataset names)',
            icon=DashIconify(icon="material-symbols:warning"),
            color='yellow',
            duration=4000,
        )]
        return notification, *no_update_10[1:]

    if dataset_store is None:
        notification = [dict(
            title='No Dataset',
            message='No dataset loaded. Please select a dataset from LOGs first.',
            icon=DashIconify(icon="material-symbols:warning"),
            color='yellow',
            duration=4000,
        )]
        return notification, *no_update_10[1:]

    session = get_session()

    delays = dataset_store.get('delays', {})

    new_dataset = Dataset(
        name=dataset_name,
        project=project_name,
        sample=sample_name,
        t=dataset_store['t'],
        V=dataset_store['RealData'],
        V_im=dataset_store['ImagData'],
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

    empty_figure = go.Figure()
    empty_figure.update_layout(
        title='Select a dataset from LOGs to view',
        xaxis_title='Time (us)',
        yaxis_title='Signal (a.u.)',
    )

    return notification, '', '', '', None, [], empty_figure, 0, None, {}


@callback(
    Output(prefix + 'dataset-store', 'data', allow_duplicate=True),
    Input({"type": "tmin-shift", 'page': page_id}, 'value'),
    State(prefix + 'dataset-store', 'data'),
    prevent_initial_call=True
)
def update_tmin(tmin_shift, dataset_store):
    if dataset_store is None:
        return dash.no_update

    dataset_store['tmin'] = tmin_shift / 1e3
    dataset_store.setdefault('delays', {})['deadtime'] = tmin_shift
    return dataset_store


@callback(
    Output(prefix + 'project-name', 'data'),
    Output(prefix + 'sample-name', 'data'),
    Input(prefix + 'project-name', 'n_clicks'),
    prevent_initial_call=False
)
def update_samples_and_projects(n_clicks):
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()

    projects = list(set(ds.project for ds in datasets))
    samples = list(set(ds.sample for ds in datasets))
    return projects, samples


@callback(
    Output(prefix + 'delays-grid', 'rowData', allow_duplicate=True),
    Input(prefix + 'experiment-type-dropdown', 'value'),
    State(prefix + 'delays-grid', 'rowData'),
    prevent_initial_call=True
)
def check_delays(exp_type, delays_row_data):
    def get_delays_by_value(options_list, value):
        """Extract the delays element from a list of dicts based on a value."""
        option = next((opt for opt in options_list if opt.get('value') == value), None)
        return option.get('delays') if option else None
    
    required_delays = get_delays_by_value(experiment_type_options, exp_type)

    delays = {row['parameter']: row['value'] for row in delays_row_data}
    new_delays = delays.copy()
    for delay in required_delays:
        if delay not in delays:
            new_delays[delay] = 0

    return [{'parameter': k, 'value': v} for k, v in new_delays.items()]


@callback(
    Output(prefix + 'tmin-warning-div', 'children'),
    Input(prefix + 'dataset-store', 'data'),
    State(prefix + 'experiment-type-dropdown', 'value'),
    prevent_initial_call=True
)
def check_tmin(store, exp_type):
    if store is None:
        return None
    delays = store.get('delays', {})

    if exp_type == '4pDEER':
        peak_time = delays.get('tau1', 0) / 1e3
    elif exp_type == '5pDEER':
        peak_time = delays.get('tau3', 0) / 1e3
    elif exp_type == 'RIDME':
        peak_time = delays.get('tau1', 0) / 1e3
    else:
        return None

    t_min = store.get('tmin', 0)
    t = np.array(store['t']) + t_min
    data_max_time = t[np.argmax(np.abs(store['RealData']))]
    threshold = 50 / 1e3

    if abs(peak_time - data_max_time) > threshold:
        return dmc.Alert(
            title="Warning: tmin may be incorrect",
            children=f"The expected peak time based on delays is {peak_time * 1e3:.0f} ns, but the data maximum is at {data_max_time * 1e3:.0f} ns. Please check that tmin is set correctly.",
            color="yellow",
            mb="md",
        )
    return None

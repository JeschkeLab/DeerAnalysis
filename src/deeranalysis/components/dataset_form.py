import dash
from dash import callback, Input, Output, State, MATCH
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import numpy as np
import datetime as dt

from deerlab import correctphase as _correctphase
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils.deerlab_options import experiment_type_options
from deeranalysis.components.data_viewer import plot_upload


# ---------------------------------------------------------------------------
# tmin shift → update store
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'dataset-store', 'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'tmin', 'page': MATCH}, 'value'),
    State({'type': 'dataset-store', 'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def update_tmin(tmin, dataset_store):
    if dataset_store is None:
        return dash.no_update
    dataset_store['tmin'] = tmin / 1e3
    dataset_store.setdefault('delays', {})['deadtime'] = tmin
    return dataset_store


# ---------------------------------------------------------------------------
# Experiment type change → ensure required delay rows are present
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'delays-grid', 'page': MATCH}, 'rowData', allow_duplicate=True),
    Input({'type': 'experiment-type-dropdown', 'page': MATCH}, 'value'),
    State({'type': 'delays-grid', 'page': MATCH}, 'rowData'),
    prevent_initial_call=True,
)
def check_delays(exp_type, delays_row_data):
    def _get_required(options, value):
        opt = next((o for o in options if o.get('value') == value), None)
        return opt.get('delays') if opt else []

    required = _get_required(experiment_type_options, exp_type)
    delays = {row['parameter']: row['value'] for row in delays_row_data}
    new_delays = delays.copy()
    for delay in required:
        if delay not in delays:
            new_delays[delay] = 0
    return [{'parameter': k, 'value': v} for k, v in new_delays.items()]

@callback(
    Output({'type': 'dataset-store', 'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'delays-grid', 'page': MATCH}, 'cellValueChanged'),
    State({'type': 'delays-grid', 'page': MATCH}, 'rowData'),
    State({'type': 'dataset-store', 'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def update_delays(_, delays_row_data, dataset_store):
    if dataset_store is None or delays_row_data is None:
        return dash.no_update
    delays = {row['parameter']: row['value'] for row in delays_row_data}
    dataset_store['delays'] = delays
    return dataset_store

# ---------------------------------------------------------------------------
# Store / experiment type change → check tmin plausibility
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'tmin-warning-div', 'page': MATCH}, 'children'),
    Input({'type': 'dataset-store', 'page': MATCH}, 'data'),
    Input({'type': 'experiment-type-dropdown', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
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
            children=(
                f"The expected peak time based on delays is {peak_time * 1e3:.0f} ns, "
                f"but the data maximum is at {data_max_time * 1e3:.0f} ns. "
                "Please check that tmin is set correctly."
            ),
            color="yellow",
            mb="md",
        )
    return None


# ---------------------------------------------------------------------------
# Populate project / sample autocomplete options from the database
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'project-name', 'page': MATCH}, 'data'),
    Output({'type': 'sample-name', 'page': MATCH}, 'data'),
    Input({'type': 'project-name', 'page': MATCH}, 'n_clicks'),
    prevent_initial_call=False,
)
def update_projects_and_samples(_n_clicks):
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()
    projects = list(set(ds.project for ds in datasets))
    samples = list(set(ds.sample for ds in datasets))
    return projects, samples


# ---------------------------------------------------------------------------
# Save dataset to database and reset the form
# ---------------------------------------------------------------------------
def _notify(title, message, icon, color, position='top-center'):
    dash.set_props('notification-container', {'sendNotifications': [dict(
        title=title, message=message,
        icon=DashIconify(icon=icon), color=color, duration=4000, position=position,
    )]})


@callback(
    Output({'type': 'project-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Output({'type': 'sample-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Output({'type': 'dataset-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Output({'type': 'dataset-store', 'page': MATCH}, 'data', allow_duplicate=True),
    Output({'type': 'delays-grid', 'page': MATCH}, 'rowData', allow_duplicate=True),
    Output({'type': 'data-viewer-plot', 'page': MATCH}, 'figure', allow_duplicate=True),
    Output({'type': 'tmin', 'page': MATCH}, 'value', allow_duplicate=True),
    Output({'type': 'metadata-content', 'page': MATCH}, 'children', allow_duplicate=True),
    Output({'type': 'metadata-modal-store', 'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'save-dataset-btn', 'page': MATCH}, 'n_clicks'),
    State({'type': 'project-name', 'page': MATCH}, 'value'),
    State({'type': 'sample-name', 'page': MATCH}, 'value'),
    State({'type': 'dataset-name', 'page': MATCH}, 'value'),
    State({'type': 'dataset-store', 'page': MATCH}, 'data'),
    State({'type': 'experiment-type-dropdown', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def save_dataset(n_clicks, project_name, sample_name, dataset_name, dataset_store, experiment_type):
    no_update_9 = (dash.no_update,) * 9

    if n_clicks is None:
        return no_update_9

    if not project_name or not sample_name or not dataset_name:
        _notify('Missing Information',
                'Please fill in all required fields (Project, Sample, and Dataset names)',
                'mdi:alert-circle-outline', 'yellow')
        return no_update_9

    if dataset_store is None:
        _notify('No Dataset',
                'No dataset loaded. Please upload or select a dataset first.',
                'mdi:alert-circle-outline', 'yellow')
        return no_update_9

    session = get_session()
    if session is None:
        _notify('Database Error', 'Could not connect to the database.',
                'material-symbols:warning', 'red')
        return no_update_9

    delays = dataset_store.get('delays', {})

    t = np.array(dataset_store['t'])
    t = t - t[0]
    tmin = dataset_store.get('tmin', 0)
    t = t + tmin

    V_real = np.array(dataset_store['RealData'])
    V_imag = np.array(dataset_store['ImagData'])
    V_real, V_imag, _ = _correctphase(V_real + 1j * V_imag, full_output=True)

    masked_indices = dataset_store.get('masked_indices', []) or []
    mask = np.ones(len(t), dtype=bool)
    if masked_indices:
        mask[np.array(masked_indices, dtype=int)] = False

    datetime_str = dataset_store['attrs'].get('datetime', None)
    measured_at = dt.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S") if datetime_str else None

    new_dataset = Dataset(
        name=dataset_name,
        project=project_name,
        sample=sample_name,
        t=t.tolist(),
        V=V_real.tolist(),
        V_im=V_imag.tolist(),
        mask=mask.tolist(),
        exp=experiment_type,
        delays=delays,
        meta=dataset_store['attrs'],
        measured_at=measured_at,
    )
    session.add(new_dataset)
    session.commit()
    session.close()

    _notify('Success',
            f"Dataset '{dataset_name}' successfully saved to project '{project_name}'!",
            'material-symbols:check-circle', 'green', position='bottom-right')
    return '', '', '', None, [], plot_upload(None), 0, None, {}

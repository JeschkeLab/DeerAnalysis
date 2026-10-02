import dash
from dash import html, dcc, callback, Input, Output, State, MATCH, ctx
from dash_iconify import DashIconify

import dash_bootstrap_components as dbc
import json
import numpy as np
import deerlab as dl
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure, dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.model_edit_modal import create_model_edit_modal
from deeranalysis.components.download_modal import create_fit_download_modal

from deeranalysis.utils.deerlab_options import (
    regparam_options, background_models, parametric_models,
    plotly_goodness_of_fit, plotly_deerlab, fit_to_dict, dists_stats_to_list,
    name_dataset_from_dict, build_model_data,plotly_dipolar_spectrum
)
from deeranalysis.components.fit_page_components import (
    fit_save_download_buttons, distance_slider, adv_fit_options_parametric,
    fit_plot,
    dist_stats_tab,
)
import deeranalysis.components.fit_page_components as fpc
from deeranalysis.utils.job_tracking import create_job, get_job
from deeranalysis.components.warnings import list_of_warnings_modal
from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict
from deeranalysis.utils.deerlab_normal import deerlab_fitting

import dash_mantine_components as dmc

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

dash.register_page(__name__)
page_id = 'parametric'

layout = html.Div([
    dmc.Title("Parametric Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dbc.Row([
        dbc.Col([
            create_dataset_modal(page_id=page_id),
            create_fit_download_modal(page_id=page_id),
            create_model_edit_modal(page_id=page_id),
            list_of_warnings_modal(page_id=page_id),
            html.Div([
                dmc.Select(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                               id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            dmc.Space(h=10),
            dmc.Select(
                label='Distance Model',
                id={'type': 'dist_model', 'page': page_id},
                data=parametric_models,
                value='dd_gauss'
            ),
            dmc.Space(h=10),
            dmc.Select(
                label='Background Model',
                id={'type': 'bg_model', 'page': page_id},
                data=background_models,
                value='bg_hom3d'
            ),
            dmc.Space(h=10),
            dmc.CheckboxGroup(
                id={'type': 'pathways-options', 'page': page_id},
                label="Pathways to include:",
                description="These pathways will be applied to all datasets, if they are feasible for the corresponding experiment.",
                children=dmc.Group([
                    dmc.Checkbox(value='1', label='1'),
                    dmc.Checkbox(value='2', label='2'),
                    dmc.Checkbox(value='3', label='3'),
                    dmc.Checkbox(value='4', label='4'),
                    dmc.Checkbox(value='5', label='5'),
                ]),
                value=['1'],
            ),
            dmc.Space(h=10),
            dmc.NumberInput(
                id={"type": "multi-start", "page": page_id},
                label="Number of Multi-Starts",
                value=1,
                min=1,
                step=1,
                description="Number of multi-starts to perform during fitting. This can help avoid local minima, but will increase fitting time.",
            ),
            fpc.distance_slider(page_id),
            dmc.Space(h=10),
            dmc.Button(
                "Edit Dipolar Model",
                id={'type': 'open-model-edit-btn', 'page': page_id},
                color="blue", variant='outline', className="mb-2 ms-1",
                leftSection=DashIconify(icon='material-symbols:edit', width=20),
            ),
            dmc.Space(h=10),
            fpc.bootstrap_controls(page_id),
            dmc.Space(h=10),
            fit_save_download_buttons(page_id),
            html.Div(id='p-fit-status'),
            fpc.queued_jobs_panel(page_id),
        ], width=3),

        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id),
                fpc.fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fpc.fit_results_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                    fpc.dipolar_spectrum_tab(page_id)
                ),
            ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9)

    ]),

    dcc.Store(id={'type':'fit-results-store','page': page_id}),
    dcc.Store(id={'type': 'fit-options', 'page': page_id}),
    dcc.Store(id={'type': 'model-params-store', 'page': page_id}),
])

@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, 'data'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return options


@callback(
    Output({'type': 'fit-options', 'page': page_id}, 'data'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    Input({'type': 'dist_model', 'page': page_id}, 'value'),
    Input({'type': 'pathways-options', 'page': page_id}, 'value'),
    Input({"type": "distance-axis", "page": page_id}, 'value'),
    Input({"type": "multi-start", "page": page_id}, 'value'),
    prevent_initial_call=True
)
def update_fit_options(bg_model_option, dist_model_name, pathways_options, distance_axis, multi_start):
    return {
        'bg_model': bg_model_option,
        'dist_model': dist_model_name,
        'pathways_options': pathways_options,
        'distance_axis': distance_axis,
        'multistart': multi_start,
    }


@callback(
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'bg_model', 'page': page_id}, 'value'),
    State({'type': 'dist_model', 'page': page_id}, 'value'),
    State({'type': 'pathways-options', 'page': page_id}, 'value'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    prevent_initial_call=True,
)
def open_model_edit_modal(n_clicks, dataset_id, bg_model_name, dist_model_name,
                          pathways, distance_axis, existing_overrides):
    if not n_clicks or not dataset_id:
        return False, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    session.close()

    pathways_int = [int(p) for p in pathways] if pathways else [1]
    model_data = build_model_data(
        dataset, bg_model_name, pathways_int, distance_axis,
        p_model_name=dist_model_name,
        existing_overrides=existing_overrides,
    )
    return True, model_data


@callback(
    Output('p-fit-status', 'children', allow_duplicate=True),
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({"type": "run-fit-btn", "page": page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit-options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    State({"type": "bootstrap-toggle", "page": page_id}, 'checked'),
    State({"type": "bootstrap-samples", "page": page_id}, 'value'),
    prevent_initial_call=True
)
def queue_fit(n_clicks, dataset_id, fit_options, model_params, bootstrap_enabled, bootstrap_samples):
    if not dataset_id:
        fpc.notify('No Dataset', 'Please select a dataset first.', 'mdi:alert-circle-outline', 'yellow')
        return dash.no_update, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    label = dataset_entry.name if dataset_entry else f"dataset {dataset_id}"
    session.close()

    params = {
        'dataset_id': dataset_id,
        'fit_options': fit_options,
        'model_params': model_params,
        'bootstrap_enabled': bootstrap_enabled,
        'bootstrap_samples': bootstrap_samples,
    }
    job_id = create_job(job_type='parametric_fit', page=page_id, label=label, params=params)
    fpc.notify('Fit Queued', f'Queued parametric fit for {label}.', 'mdi:clock-outline', 'blue')
    return dash.no_update, job_id


@callback(
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    Input({'type': 'fit-options', 'page': page_id}, 'data'),
    Input({'type': 'model-params-store', 'page': page_id}, 'data'),
    Input({"type": "bootstrap-toggle", "page": page_id}, 'checked'),
    Input({"type": "bootstrap-samples", "page": page_id}, 'value'),
    prevent_initial_call=True,
)
def invalidate_pending_auto_load(*_args):
    """Any change to a fit parameter after queueing means the eventual result would no longer
    match what's on screen — stop watching for it so it doesn't silently auto-load."""
    return None


@callback(
    Output({'type':'fit-results-store','page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type": "save-fit-btn", "page": page_id}, 'disabled', allow_duplicate=True),
    Output({"type": "download-fit-btn", "page": page_id}, 'disabled', allow_duplicate=True),
    Output({'type': 'fit-plot-showpathways', 'page': page_id}, 'checked', allow_duplicate=True),
    Output({'type': 'bg_model', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'dist_model', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'pathways-options', 'page': page_id}, 'value', allow_duplicate=True),
    Output({"type": "distance-axis", "page": page_id}, 'value', allow_duplicate=True),
    Output({"type": "multi-start", "page": page_id}, 'value', allow_duplicate=True),
    Output({'type': 'model-params-store', 'page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "bootstrap-toggle", "page": page_id}, 'checked', allow_duplicate=True),
    Output({"type": "bootstrap-samples", "page": page_id}, 'value', allow_duplicate=True),
    Input({"type": "job-load-request", "page": page_id}, "data"),
    prevent_initial_call=True,
)
def load_queued_result(job_id):
    # Dataset dropdown is deliberately not restored — see the note in nonparametric.py's
    # load_queued_result for why (it would trigger plot_dataset and wipe the loaded result).
    no_update_12 = (dash.no_update,) * 12
    if not job_id:
        return no_update_12
    job = get_job(job_id)
    if job is None or job.status != 'done' or not job.result_data:
        return no_update_12
    fit_dict = job.result_data
    p = job.params or {}
    fo = p.get('fit_options') or {}
    return (
        fit_dict, fit_dict.get('model_description', ''), False, False, False,
        fo.get('bg_model'), fo.get('dist_model'), fo.get('pathways_options'),
        fo.get('distance_axis'), fo.get('multistart'),
        p.get('model_params'), p.get('bootstrap_enabled'), p.get('bootstrap_samples'),
    )



@callback(
    Output('p-fit-status', 'children'),
    Input({"type": "save-fit-btn", "page": page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type':'fit-results-store','page': page_id}, 'data'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_id, dataset_store):
    if not dataset_store or not dataset_id:
        print(f"No fit results to save or no dataset selected.")
        return dash.no_update

    session = get_session()
    new_fit = Fit(
        dataset_id=dataset_id,
        name=name_dataset_from_dict(dataset_store),
        **dataset_store
    )
    session.add(new_fit)
    session.commit()
    session.close()

    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)


@callback(
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
    Output({"type": "dip-spectrum-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Input({'type': 'fit-results-store', 'page': page_id}, 'data'),
    prevent_initial_call=True
)
def update_plots_tables(fit_dict):

    if not fit_dict or 'data' not in fit_dict:
        return dash.no_update
    fit = dl.json_loads(fit_dict['data'])
    gof_fig = plotly_goodness_of_fit(fit)
    dip_spectrum_fig = plotly_dipolar_spectrum(fit)

    dist_stats_dict = fit_dict['dist_stats']
    dist_stats_output = {
        "head": ["Statistic", "Value", "Confidence Interval (95%)"],
        "body": [
            [k, f"{v['value']:.3f}", f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]" if v['ci'] else "N/A"]
            for k, v in dist_stats_dict.items()
        ]
    }
    return gof_fig, dist_stats_output,dip_spectrum_fig
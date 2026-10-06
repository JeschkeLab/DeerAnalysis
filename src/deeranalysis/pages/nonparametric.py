import json
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import xarray as xr
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.download_modal import create_fit_download_modal
from deeranalysis.components.model_edit_modal import create_model_edit_modal
from deeranalysis.utils.deerlab_options import background_models, plotly_goodness_of_fit, name_dataset_from_dict, build_model_data, plotly_lcurve, plotly_dipolar_spectrum
from deeranalysis.utils.job_tracking import create_job, get_job
from deeranalysis.components.warnings import list_of_warnings_modal
from deeranalysis.utils.deerlab_options import background_models, plotly_goodness_of_fit, dists_stats_to_list, fit_to_dict,name_dataset_from_dict, build_model_data, plotly_lcurve, plotly_dipolar_spectrum

from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict, warnings_from_dict

import deeranalysis.components.fit_page_components as fpc
from deeranalysis.components.jobs_drawer import queued_jobs_panel

dash.register_page(__name__)
page_id='non-parametric'


layout = html.Div([
    dmc.Title("Non-Parametric Fit", order=1, mb="md"),
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
                label='Background Model',
                id={'type': 'bg_model', 'page': page_id},
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),     
            fpc.pathway_input(page_id),
            # Small vertical space
            dmc.Space(h=10),    
            
            dmc.Space(h=10),
            fpc.distance_slider(page_id),
            dmc.Space(h=10),
            dmc.Button("Edit Dipolar Model", id={'type': 'open-model-edit-btn', 'page': page_id}, color="blue", variant='outline', className="mb-2 ms-1", leftSection=DashIconify(icon='material-symbols:edit', width=20)),
            
            dmc.Space(h=10),
            dmc.Group([
                fpc.compactness_controls(page_id),    
                fpc.bootstrap_controls(page_id),
            ],gap="md", align="center"),
            dmc.Space(h=10),
            fpc.fit_name_input(page_id),
            dmc.Space(h=10),
            fpc.adv_fit_options_regularisation(page_id),
            dmc.Space(h=10),
            fpc.fit_save_download_buttons(page_id),
            dmc.Space(h=10),
            
            html.Div(id='np-fit-status'),
            queued_jobs_panel(page_id),
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id),
                fpc.fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fpc.fit_results_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                    fpc.L_curve_tab(page_id),
                    fpc.dipolar_spectrum_tab(page_id)
                )
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
                    
        ], width=9)
    ]),
    
    # Hidden store for fit results
    dcc.Store(id={'type':'fit-results-store','page': page_id}),
    # Hidden store for user-edited model parameter overrides
    dcc.Store(id={'type': 'model-params-store', 'page': page_id}),
    dcc.Store(id={'type': 'adv_options', 'page': page_id}, data={'regparam': 'bic', 'regparamrange': [1e-8,1e2]}),
])

@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, 'data'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset.id, Dataset.name).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return options

@callback(
    Output({'type': 'adv_options', 'page': page_id}, 'data'),
    Input({"type": "regparam-method", "page": page_id}, "value"),
    Input({"type": "regparam-search-method", "page": page_id}, "value"),
    Input({"type": "regparam-grid-size", "page": page_id}, "value"),
    Input({"type": "fixed-alpha", "page": page_id}, "value"),
)
def update_adv_options(regparam_method,search_method, grid_size, fixed_alpha):
    output = {}

    if search_method == 'fixed':
        output['regparam'] = fixed_alpha
    else:
        output['regparam'] = regparam_method

    searchrange = [1e-8,1e3]
    if search_method == 'grid':
        output['regparamrange'] = 10**np.linspace(np.log10(searchrange[0]),np.log10(searchrange[1]),grid_size)
    elif search_method == 'brent':
        output['regparamrange'] = searchrange
    
    return output

@callback(
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'bg_model', 'page': page_id}, 'value'),
    State({'type': 'pathways-options', 'page': page_id}, 'value'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    prevent_initial_call=True,
)
def open_model_edit_modal(n_clicks, dataset_id, bg_model_name, pathways, distance_axis, existing_overrides):
    if not n_clicks or not dataset_id:
        return False, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    session.close()

    pathways_int = [int(p) for p in pathways] if pathways else [1]
    model_data = build_model_data(dataset, bg_model_name, pathways_int, 
                                  distance_axis, existing_overrides=existing_overrides)
    return True, model_data




@callback(
    Output('np-fit-status', 'children', allow_duplicate=True),
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({"type": "run-fit-btn", "page": page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'bg_model', 'page': page_id}, 'value'),
    State({"type": "compactness-toggle", "page": page_id}, 'checked'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State({'type': 'pathways-options', 'page': page_id}, 'value'),
    State({'type': 'adv_options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    State({"type": "bootstrap-toggle", "page": page_id}, 'checked'),
    State({"type": "bootstrap-samples", "page": page_id}, 'value'),
    State({'type': 'fit-name-input', 'page': page_id}, 'value'),
    prevent_initial_call=True,
)
def queue_fit(n_clicks, dataset_id, bg_model_option, compactness, distance_axis, pathways_options,
              adv_options, model_params, bootstrap_enabled, bootstrap_samples, fit_name):
    if not dataset_id:
        fpc.notify('No Dataset', 'Please select a dataset first.', 'mdi:alert-circle-outline', 'yellow')
        return dash.no_update, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    label = dataset_entry.name if dataset_entry else f"dataset {dataset_id}"
    session.close()

    params = {
        'fit_name': fit_name,
        'dataset_id': dataset_id,
        'bg_model_option': bg_model_option,
        'compactness': compactness,
        'distance_axis': distance_axis,
        'pathways_options': pathways_options,
        'adv_options': adv_options,
        'model_params': model_params,
        'bootstrap_enabled': bootstrap_enabled,
        'bootstrap_samples': bootstrap_samples,
    }
    job_id = create_job(job_type='non-parametric_fit', page=page_id, label=label, params=params)
    fpc.notify('Fit Queued', f'Queued non-parametric fit for {label}.', 'mdi:clock-outline', 'blue')
    return dash.no_update, job_id


@callback(
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    Input({"type": "compactness-toggle", "page": page_id}, 'checked'),
    Input({"type": "distance-axis", "page": page_id}, 'value'),
    Input({'type': 'pathways-options', 'page': page_id}, 'value'),
    Input({'type': 'adv_options', 'page': page_id}, 'data'),
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
    Output({'type': 'fit-name-input', 'page': page_id}, 'value'),
    Output({'type': 'fit-name-auto', 'page': page_id}, 'data'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    Input({'type': 'pathways-options', 'page': page_id}, 'value'),
    Input({"type": "compactness-toggle", "page": page_id}, 'checked'),
    Input({"type": "bootstrap-toggle", "page": page_id}, 'checked'),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit-name-input', 'page': page_id}, 'value'),
    State({'type': 'fit-name-auto', 'page': page_id}, 'data'),
)
def autofill_fit_name(bg_model, pathways, compactness, bootstrap, dataset_id, current_name, last_auto_name):

    fit_name = fpc.create_fit_name('non-parametric', bg_model, pathways, compactness, bootstrap)
    if fit_name is not None and dataset_id is not None:
        _, fit_name = fpc.validate_fit_name(fit_name,dataset_id, suggest_new=True)
    
    return fpc.autofill_fit_name(fit_name, current_name, last_auto_name)


@callback(
    Output({'type':'fit-results-store','page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type": "save-fit-btn", "page": page_id}, 'disabled', allow_duplicate=True),
    Output({'type':"download-fit-btn",'page':page_id}, 'disabled', allow_duplicate=True),
    Output({'type': 'fit-plot-showpathways', 'page': page_id}, 'checked', allow_duplicate=True),
    Output({'type': 'bg_model', 'page': page_id}, 'value', allow_duplicate=True),
    Output({"type": "compactness-toggle", "page": page_id}, 'checked', allow_duplicate=True),
    Output({"type": "distance-axis", "page": page_id}, 'value', allow_duplicate=True),
    Output({'type': 'pathways-options', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'adv_options', 'page': page_id}, 'data', allow_duplicate=True),
    Output({'type': 'model-params-store', 'page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "bootstrap-toggle", "page": page_id}, 'checked', allow_duplicate=True),
    Output({"type": "bootstrap-samples", "page": page_id}, 'value', allow_duplicate=True),
    Input({"type": "job-load-request", "page": page_id}, "data"),
    prevent_initial_call=True,
)
def load_queued_result(job_id):
    # Note: the dataset dropdown is deliberately NOT restored here — changing it would trigger
    # fit_page_components.plot_dataset (Input on dataset-dropdown), which overwrites
    # fit-results-store with a bare dataset preview and would wipe out the fit result we just
    # loaded a moment later.
    no_update_13 = (dash.no_update,) * 13
    if not job_id:
        return no_update_13
    job = get_job(job_id, with_result=True)
    if job is None or job.status != 'done' or not job.result_data:
        return no_update_13
    fit_dict = job.result_data
    p = job.params or {}
    return (
        fit_dict, fit_dict.get('model_description', ''), False, False, False,
        p.get('bg_model_option'), p.get('compactness'),
        p.get('distance_axis'), p.get('pathways_options'), p.get('adv_options'),
        p.get('model_params'), p.get('bootstrap_enabled'), p.get('bootstrap_samples'),
    )


@callback(
    Output('np-fit-status', 'children'),
    Input({"type": "save-fit-btn", "page": page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id},'value'),
    State({'type':'fit-results-store','page': page_id}, 'data'),
    State({'type': 'fit-name-input', 'page': page_id}, 'value'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_id,dataset_store,fit_name):
    if not dataset_store or not dataset_id:
        print(f"No fit results to save or no dataset selected.")
        return dash.no_update
        
    session = get_session()
    
    new_fit = Fit(
        dataset_id=dataset_id,
        name=fit_name,
        **dataset_store
    )
    
    session.add(new_fit)
    session.commit()
    session.close()
    
    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)

# @callback(
#     Output({"type": "fit-dl-modal",'page': page_id}, "opened"),
#     Output({"type": "fit-dl-store",'page': page_id}, "data"),
#     Input('np-download-fit-btn', 'n_clicks'),
#     State({'type':'fit-results-store','page': page_id}, 'data'),

#     prevent_initial_call=True
# )
# def download_fit(n_clicks, fit_store):
#     if n_clicks is None or not fit_store:
#         return False, dash.no_update
    
#     return True, fit_store

@callback(
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "l-curve-plot", "page": page_id}, 'figure', allow_duplicate=True),
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
    if fit_dict.get('fit_type') != 'background':
        l_curve_fig = plotly_lcurve(fit)
    else:
        l_curve_fig = plotly_lcurve(None)
    dip_spectrum_fig = plotly_dipolar_spectrum(fit)

    dist_stats_dict = fit_dict['dist_stats']
    dist_stats_output = {
        "head": ["Statistic", "Value", "Confidence Interval (95%)"],
        "body": [
            [k, f"{v['value']:.3f}", f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]" if v['ci'] else "N/A"]
            for k, v in dist_stats_dict.items()
        ]
    }
    return gof_fig, l_curve_fig, dist_stats_output, dip_spectrum_fig
    

    


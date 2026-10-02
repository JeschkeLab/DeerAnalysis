import json
import copy
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.database import get_session, Dataset, Fit, fit_global_datasets, fit_siblings
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.download_modal import create_fit_download_modal

from deeranalysis.components.model_edit_modal import create_model_edit_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, plotly_deerlab,dists_stats_to_list, fit_to_dict,name_dataset_from_dict
from deeranalysis.components.fit_page_components import fit_save_download_buttons,distance_slider,adv_fit_options_parametric
import deeranalysis.components.fit_page_components as fpc
import deeranalysis.components.fpc_global as fpcg

from deeranalysis.utils.deerlab_population import build_population_model_data
from deeranalysis.utils.job_tracking import create_job, get_job
from deeranalysis.utils.deerlab_population import deerlab_population_fitting, determine_pop_P, build_population_model_data
from deeranalysis.components.warnings import list_of_warnings_modal
from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict


dash.register_page(__name__)

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

startup_message = dmc.Alert("Multi-population fitting is designed for globally fitting multiple datasest of different samples where there is more than 1-population presenet and where the ratio of these populations changes.",title="Note!", color="blue",withCloseButton=True)

page_id='population'

# Overwrite the default parametric models permittable

parametric_models = [
    {'label': '1 Gaussian', 'value': 'dd_gauss'},
    # {'label': '1 3D Rice', 'value': 'dd_rice'},
]

# Overwrite the default background models permittable
background_models = [
    {'label': 'Homogeneous 3D', 'value': 'bg_hom3d'},
]

dummy_download_modal = dmc.Modal(
    id={"type": "fit-dl-modal-not", "page": page_id},
    title="Download Fit Results",
    children=[
        dmc.Text("Downloading Global Fit Results is not currently supported. Please save the fit and download each fit independently from the fits page."),
    ],    size="lg",
    centered=True,
)
layout = html.Div([
    dmc.Title("Multi-Population Global Fitting", order=1, mb="md"),
    dmc.Divider(mb="lg"),


    dbc.Row([
        dbc.Col([
            startup_message,
            create_dataset_modal(page_id=page_id),
            create_model_edit_modal(page_id=page_id),
            list_of_warnings_modal(page_id=page_id),
            dummy_download_modal,
            html.Div([
                dmc.Group([dmc.MultiSelect(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", description="Between 2 and 5 dataset should selected.")],style={'flex': '1 1 0',"flexGrow":1}),
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
                value=['1'], # Default selected pathways
            ),
            # Small vertical space
            dmc.Space(h=10),
            dmc.NumberInput(
                label="Number of Populations",
                id={'type': 'n_pops', 'page': page_id},
                value=2,
                min=1,
                max=5,
                step=1,
            ),
            dmc.Select(
                label='Parametric Distance Model',
                id={"type": "dd_model", "page": page_id},
                data=parametric_models,
                value='dd_gauss',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),
            distance_slider(page_id),
            dmc.Space(h=10),
            dmc.Button("Edit Dipolar Model", id={'type': 'open-model-edit-btn', 'page': page_id}, color="blue", variant='outline', className="mb-2 ms-1", leftSection=DashIconify(icon='material-symbols:edit', width=20)),
            
            dmc.Space(h=10),
            fpc.bootstrap_controls(page_id),
            dmc.Space(h=10),

            fit_save_download_buttons(page_id),
            html.Div(id={'type':'fit-status','page': page_id}),
            fpc.queued_jobs_panel(page_id),
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpcg.plotly_deerlab_pagination(page_id=page_id,show_population_option=True),
                fpc.fit_results_tabs(
                    fpcg.overview_tab_population(page_id),
                    fpc.fit_results_tab(page_id),
                    fpcg.goodness_of_fit_tab_pagination(page_id),
                    fpcg.dipolar_spectrum_tab_pagination(page_id)
                ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9) # dbc.col

        
    ]),
    dcc.Store(id={'type': 'fit-results-store-multi', 'page': page_id}),
    dcc.Store(id={'type': 'fit_options', 'page': page_id}),
    dcc.Store(id={'type': 'model-params-store', 'page': page_id}),
])

# ----- Callbacks for input option updates and checking -----

@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, "error", allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, "value"),
    prevent_initial_call=True
)
def check_dataset_input(ds_inputs):
    # Check that between 2 and 5 datasets are selected, otherwise show an error message
    if not ds_inputs:
        return None
    elif len(ds_inputs) < 2:
        return "Please select at least 2 datasets."
    elif len(ds_inputs) > 5:
        return "Please select no more than 5 datasets."
    else:
        return None
    
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
# ----- Callbacks for Updating Fit Options and Running Fit -----


@callback(
    Output({'type': 'fit_options', 'page': page_id}, 'data'),
    Input({'type': 'n_pops', 'page': page_id}, 'value'),
    Input({"type": "dd_model", "page": page_id}, 'value'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    Input({"type": "distance-axis", "page": page_id}, 'value'),
    Input({'type': 'pathways-options', 'page': page_id}, 'value'),
)
def update_fit_options(n_pops,dd_model,bg_model,distance_axis,pathways_options):
    options = {
        'n_pops': n_pops,
        'dd_model': dd_model,
        'bg_model': bg_model,
        'distance_axis': distance_axis,
        'pathways_options': pathways_options
    }
    return options




# ----- Model Edit Modal -----

@callback(
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'bg_model', 'page': page_id}, 'value'),
    State({"type": "dd_model", "page": page_id}, 'value'),
    State({'type': 'pathways-options', 'page': page_id}, 'value'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State({'type': 'n_pops', 'page': page_id}, 'value'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    prevent_initial_call=True,
)
def open_model_edit_modal(n_clicks, dataset_ids, bg_model_name, dd_model_name,
                          pathways, distance_axis, n_pops, existing_overrides):
    """Opens the model edit modal, building the full merged+linked global model so per-dataset params show up."""
    if not n_clicks or not dataset_ids:
        return False, dash.no_update

    session = get_session()
    datasets = []
    for ds_id in dataset_ids:
        entry = session.query(Dataset).filter_by(id=ds_id).first()
        ds = dataarray_from_database_entry(entry)
        datasets.append(ds.assign_coords(t=ds.t.values))
    session.close()

    pathways_int = [int(p) for p in pathways] if pathways else [1]
    model_data = build_population_model_data(
        datasets, bg_model_name, pathways_int,
        dd_model_name=dd_model_name,
        n_pops=n_pops or 2,
        existing_overrides=existing_overrides,
    )
    return True, model_data


# ----- Main Fitting Callback -----


@callback(
    Output({'type':'fit-status','page': page_id}, 'children', allow_duplicate=True),
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit_options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    State({"type": "bootstrap-toggle", "page": page_id}, 'checked'),
    State({"type": "bootstrap-samples", "page": page_id}, 'value'),
    prevent_initial_call=True
)
def queue_fit(n_clicks, dataset_ids, fit_options, model_params, bootstrap_enabled, bootstrap_samples):
    if not dataset_ids:
        fpc.notify('No Datasets', 'Please select between 2 and 5 datasets first.', 'mdi:alert-circle-outline', 'yellow')
        return dash.no_update, dash.no_update

    session = get_session()
    names = []
    for ds_id in dataset_ids:
        entry = session.query(Dataset).filter_by(id=ds_id).first()
        names.append(entry.name if entry else str(ds_id))
    session.close()
    label = ", ".join(names)

    params = {
        'dataset_ids': dataset_ids,
        'fit_options': fit_options,
        'model_params': model_params,
        'bootstrap_enabled': bootstrap_enabled,
        'bootstrap_samples': bootstrap_samples,
    }
    job_id = create_job(job_type='population_fit', page=page_id, label=label, params=params)
    fpc.notify('Fit Queued', f'Queued population fit for {label}.', 'mdi:clock-outline', 'blue')
    return dash.no_update, job_id


@callback(
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    Input({'type': 'fit_options', 'page': page_id}, 'data'),
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
    Output({'type': 'fit-results-store-multi', 'page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled', allow_duplicate=True),
    Output({"type":"download-fit-btn","page":page_id}, 'disabled', allow_duplicate=True),
    Output({'type': 'bg_model', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'pathways-options', 'page': page_id}, 'value', allow_duplicate=True),
    Output({'type': 'n_pops', 'page': page_id}, 'value', allow_duplicate=True),
    Output({"type": "dd_model", "page": page_id}, 'value', allow_duplicate=True),
    Output({"type": "distance-axis", "page": page_id}, 'value', allow_duplicate=True),
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
    fit_store = job.result_data
    p = job.params or {}
    fo = p.get('fit_options') or {}
    return (
        fit_store, fit_store.get('model_description', ''), False, False,
        fo.get('bg_model'), fo.get('pathways_options'), fo.get('n_pops'), fo.get('dd_model'),
        fo.get('distance_axis'), p.get('model_params'), p.get('bootstrap_enabled'), p.get('bootstrap_samples'),
    )

# ----- Save and Download Callbacks -----

@callback(
    Output({'type':'fit-status','page': page_id}, 'children'),
    Input({'type':'save-fit-btn','page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id},'value'),
    State({'type':'fit-results-store-multi','page': page_id}, 'data'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_ids, dataset_store):
    """Saves the current fit results to the database, once for each dataset.
    The fit_global_datasets and fit_siblings relationships are also populated so that
    each saved Fit knows which other datasets and sibling fits belong to the same
    global run."""
    if not dataset_store or not dataset_ids:
        print("No fit results to save or no dataset selected.")
        return dash.no_update

    new_fits = []
    session = get_session()

    fit_name = name_dataset_from_dict(dataset_store)

    # Fields shared across all per-dataset Fit rows
    shared = {
        'engine':            dataset_store.get('engine'),
        'fit_type':          dataset_store.get('fit_type'),
        'bg_model':          dataset_store.get('bg_model'),
        'dist_model':        dataset_store.get('dist_model'),
        'r':                 dataset_store.get('r'),
        'pathways':          dataset_store.get('pathways'),
        'model_description': dataset_store.get('model_description'),
        'data':              dataset_store.get('data'),
    }

    gof_list = dataset_store.get('gof', [None] * len(dataset_ids))
    background_list = dataset_store.get('background', [None] * len(dataset_ids))

    for i, ds_id in enumerate(dataset_ids):
        new_fit = Fit(
            dataset_id=ds_id,
            name=fit_name,
            t=dataset_store['t'][i],
            model=dataset_store['model'][i],
            P_model=dataset_store['P_model'][i],
            PUncert=dataset_store['PUncert'][i],
            background=background_list[i],
            gof=gof_list[i],
            **shared,
        )
        session.add(new_fit)
        new_fits.append(new_fit)

    session.flush()
    for fit in new_fits:
        session.execute(fit_global_datasets.insert().values([
            {'fit_id': fit.id, 'dataset_id': ds_id}
            for ds_id in dataset_ids if ds_id != fit.dataset_id
        ]))
        session.execute(fit_siblings.insert().values([
            {'fit_id': fit.id, 'sibling_fit_id': f.id}
            for f in new_fits if f.id != fit.id
        ]))

    session.commit()
    session.close()

    return dbc.Alert("Fit saved successfully!", color="success", duration=4000)

@callback(
    Output({"type": "fit-dl-modal-not",'page': page_id}, "opened"),
    Input({'type':'download-fit-btn','page': page_id}, 'n_clicks'),
    State({'type':'fit-results-store-multi','page': page_id}, 'data'),

    prevent_initial_call=True
)
def download_fit(n_clicks, fit_store):
    if n_clicks is None or not fit_store:
        return False
    
    return True
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.database import get_session, Dataset, Fit,fit_global_datasets, fit_siblings
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.download_modal import create_fit_download_modal
from deeranalysis.components.model_edit_modal import create_model_edit_modal

import deeranalysis.components.fit_page_components as fpc
import deeranalysis.components.fpc_global as fpcg
from deeranalysis.utils.deerlab_options import background_models, fit_to_dict,name_dataset_from_dict,dists_stats_to_list
from deeranalysis.utils.deerlab_global import deerlab_global_fitting, extract_global_P, build_global_model_data


import traceback
dash.register_page(__name__)

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

page_id='global'

startup_message = dmc.Alert("Only a basic global fitting is implemented for full customisability please use the scripted version of DeerLab.", title="Note!", color="blue",withCloseButton=True)

# Overwrite the default background models permittable
background_models = [
    {'label': 'Homogeneous 3D', 'value': 'bg_hom3d'},
]

layout = html.Div([
    dmc.Title("Non-Parametric Global Fitting", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    dbc.Row([
        dbc.Col([
            startup_message,
            create_dataset_modal(page_id=page_id),
            create_fit_download_modal(page_id=page_id),
            create_model_edit_modal(page_id=page_id),
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
                description="These pathways will be applied to all datasets, if they are fesiable for the corresponding experiment.",
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
            dmc.Text("Adv. Options:", size="sm", fw=500, mb=4),        
            dmc.Chip('Compactness', id={'type': 'compactness-option', 'page': page_id}, value=False, checked=False),
            dmc.Space(h=10),
            # dmc.Text("Distance Axis:", size="sm", fw=500, mb=4),
            fpc.distance_slider(page_id),
            dmc.Space(h=10),
            dmc.Text("Global Fitting:", size="sm", fw=500, mb=4),
            dmc.Group(dmc.ChipGroup([
                dmc.Chip('P(r)',value='pr', checked=False),
                dmc.Chip('Background',value='background', checked=False),
                dmc.Chip('Modulation Depth',value='mod-depth', checked=False),
            ],
            multiple=True,
            id={'type':'global-fitting','page': page_id},
            value=['pr'],
            )),
            dmc.Space(h=10),
            fpc.adv_fit_options_regularisation(page_id),            
            dmc.Space(h=10),
            dmc.Button("Edit Dipolar Model", id={'type': 'open-model-edit-btn', 'page': page_id}, color="blue", variant='outline', className="mb-2 ms-1", leftSection=DashIconify(icon='material-symbols:edit', width=20)),
            dmc.Space(h=10),
            fpc.fit_save_download_buttons(page_id),
            
            html.Div(id={'type':'fit-status','page': page_id})
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpcg.plotly_deerlab_pagination(page_id=page_id),
                fpc.fit_results_tabs(
                    fpcg.overview_tab_global(page_id),
                    fpc.fit_results_tab(page_id),
                    fpcg.goodness_of_fit_tab_pagination(page_id),
                    fpc.dist_stats_tab(page_id),
                ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9) # dbc.col
    ]),
    
    # Hidden store for fit results
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
    Output({'type': 'global-fitting', 'page': page_id}, 'value'),
    Input({'type': 'global-fitting', 'page': page_id}, 'value'),
    State({'type': 'global-fitting', 'page': page_id}, 'value'),
    prevent_initial_call=True
)
def ensure_one_selected(value, previous_value):
    if not value:
        return previous_value or ['pr']
    return value

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
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit_options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
prevent_initial_call=True,
)
def open_model_edit_modal(n_clicks, dataset_ids, fit_options,existing_overrides):
    if not n_clicks or not dataset_ids:
        return False, dash.no_update


    pathways = fit_options.get('pathways_options', ['1'])
    
    session = get_session()
    datasets = []
    for ds_id in dataset_ids:
        entry = session.query(Dataset).filter_by(id=ds_id).first()
        ds = dataarray_from_database_entry(entry)
        datasets.append(ds.assign_coords(t=ds.t.values))
    session.close()

    pathways_int = [int(p) for p in pathways] if pathways else [1]

    model_data = build_global_model_data(
        datasets,
        bgmodel =fit_options.get('bg_model', 'bg_hom3d'),
        linked_params = fit_options.get('linked_params', ['pr']),
        pathways = pathways_int,
        existing_overrides=existing_overrides

    )
    return True, model_data


# ----- Callbacks for Updating Fit Options and Running Fit -----

@callback(
    Output({'type': 'fit_options', 'page': page_id}, 'data'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    Input({'type': 'compactness-option', 'page': page_id}, 'checked'),
    Input({"type": 'distance-axis', "page": page_id}, 'value'),
    Input({'type': 'pathways-options', 'page': page_id}, 'value'),
    Input({'type': 'global-fitting','page': page_id}, 'value'),
    Input({'type': 'regparam-method', 'page': page_id}, 'value'),
)
def update_fit_options(bg_model_option,compactness,distance_axis,pathways_options,linked_params, regparam_method):
    options = {
        'bg_model': bg_model_option,
        'compactness': compactness,
        'distance_axis': distance_axis,
        'pathways_options': pathways_options,
        'linked_params': linked_params,
        'regparam_method': regparam_method
    }
    return options


@callback(
    # Output({'type': 'fit-results-store-multi', 'page': page_id}, 'data'),
    # Output({"type": "fit-plot-figures-store", "page": page_id}, 'data'),
    # Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    # Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    # Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
    # Output({"type":"save-fit-btn","page":page_id}, 'disabled'),
    # Output({"type":"download-fit-btn","page":page_id}, 'disabled'),
    Output({'type': 'fit-results-store-multi', 'page': page_id}, 'data'),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled'),
    Output({"type":"download-fit-btn","page":page_id}, 'disabled'),

    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit_options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    running=[(Output({"type":"run-fit-btn","page":page_id}, 'loading'), True, False)],
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, fit_options, model_overrides):
    if not dataset_id:
        return dash.no_update, dash.no_update, True, True
    
    session = get_session()
    datasets = []
    dataset_names = []
    for dataset_id in dataset_id:
        dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
        if dataset_entry is None:
            print(f"Dataset with id {dataset_id} not found in the database.")
        dataset = dataarray_from_database_entry(dataset_entry)
        dataset_names.append(dataset_entry.name)    
        dataset = dataset.assign_coords(t=dataset.t.values)
        datasets.append(dataset)
    session.close()



    distance_axis = fit_options.get('distance_axis', [0, 5])
    bg_model_option = fit_options.get('bg_model', 'bg_hom3d')
    pathways_options = fit_options.get('pathways_options', ['1'])
    regparam_option = fit_options.get('regparam_method', 'bic')
    linked_params = fit_options.get('linked_params', ['pr'])

    bg_model = getattr(dl, bg_model_option, dl.bg_hom3d)
    pathways = [int(p) for p in pathways_options]
    print(pathways)
    r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range

    try:
        n_datasets = len(datasets)
        fit = deerlab_global_fitting(datasets,linked_params,
                                bg_model=bg_model, r=r, pathways=pathways,
                                model_overrides=model_overrides)
        fit.n_datasets = n_datasets
    except Exception as e:
        print(f"Error during fitting: {e}")
        traceback.print_exc()
        return dash.no_update, f"Error during fitting: {e}", True, True
    
    
    fit_store = fit_to_dict(fit,n_datasets)

    return fit_store, fit.__str__(), False, False
    # figures_store = []


def fit_to_dict(fit,n_datasets):
    """"
    Converts fit results to a dictionary for storage in the database. 
    This version is specific for population fitting where multiple fits are produced
    """

    output = {}
    output['engine'] = 'DeerLab'
    output['fit_type'] = 'Non-Parametric Global'
    output['bg_model'] = fit.bg_model.name if fit.bg_model else None
    # output['dist_model'] = fit.Pmodel.name if hasattr(fit, 'Pmodel') else None
    output['pathways'] = fit.pathways[0] if hasattr(fit, 'pathways') and fit.pathways else []
    output['r'] = fit.r.tolist() if fit.r is not None else None
    output['model_description'] = fit.__str__() if fit is not None else None
    output['data'] = dl.json_dumps(fit) if fit is not None else None

    output['t'] = [fit.t[i].tolist() for i in range(n_datasets)] if fit.t is not None else None
    output['V'] = [fit.Vexp[i].tolist() for i in range(n_datasets)] if fit.Vexp is not None else None
    output['model'] = [fit.model[i].tolist() for i in range(n_datasets)] if fit.model is not None else None
    # output['background'] = [fit.background[i].tolist() for i in range(n_datasets)] if fit.background is not None else [None] * n_datasets
    output['P_model'] = [fit.P[i].tolist() for i in range(n_datasets)]
    output['PUncert'] = [fit.PUncert[i].to_dict() for i in range(n_datasets)]
    output['gof'] = [fit.stats[i] for i in range(n_datasets)]
    output['dist_stats'] = [dists_stats_to_list(*dl.diststats(fit.r, fit.P[i], fit.PUncert[i])) for i in range(n_datasets)]
    return output


# ----- Save and Download Callbacks -----

@callback(
    Output({'type':'fit-status','page': page_id}, 'children'),
    Input({'type':'save-fit-btn','page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id},'value'),
    State({'type':'fit-results-store-multi','page': page_id}, 'data'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_ids,dataset_store):
    """Saves the current fit results to the database, once for each dataset. The global datasest and sibling fit relantionships are also filled in.
    
    # Get sibling fit IDs
        sibling_ids = session.execute(
            fit_siblings.select().where(fit_siblings.c.fit_id == fit.id)
        ).fetchall()

    # Get global dataset IDs
        global_ds_ids = session.execute(
            fit_global_datasets.select().where(fit_global_datasets.c.fit_id == fit.id)
        ).fetchall()
"""
    if not dataset_store or not dataset_ids:
        print(f"No fit results to save or no dataset selected.")
        return dash.no_update

    new_fits = []   
    session = get_session()

    for i, ds_id in enumerate(dataset_ids):
        
        new_fit = Fit(
            dataset_id=ds_id,
            name=name_dataset_from_dict(dataset_store[i]),
            **dataset_store[i],
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
    Output({"type": "fit-dl-modal",'page': page_id}, "opened"),
    Output({"type": "fit-dl-store",'page': page_id}, "data"),
    Input({'type':'download-fit-btn','page': page_id}, 'n_clicks'),
    State({'type':'fit-results-store-multi','page': page_id}, 'data'),

    prevent_initial_call=True
)
def download_fit(n_clicks, fit_store):
    if n_clicks is None or not fit_store:
        return False, dash.no_update
    
    return True, fit_store
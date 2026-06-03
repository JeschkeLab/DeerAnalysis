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

from deeranalysis.utils.deerlab_population import deerlab_population_fitting, determine_pop_P, build_population_model_data

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
            
            fit_save_download_buttons(page_id),
            html.Div(id={'type':'fit-status','page': page_id})
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpcg.plotly_deerlab_pagination(page_id=page_id,show_population_option=True),
                fpc.fit_results_tabs(
                    fpcg.overview_tab_population(page_id),
                    fpc.fit_results_tab(page_id),
                    fpcg.goodness_of_fit_tab_pagination(page_id),
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
    Output({'type': 'fit-results-store-multi', 'page': page_id}, 'data'),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled'),
    Output({"type":"download-fit-btn","page":page_id}, 'disabled'),

    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit_options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    running=[(Output({"type":"run-fit-btn","page":page_id}, 'loading'), True, False)],
    prevent_initial_call=True
)
def run_fit(n_clicks, dataset_id, fit_options, model_params):
    
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
    dd_model_option = fit_options.get('dd_model', 'dd_gauss')
    n_pops = fit_options.get('n_pops', 2)

    bg_model = getattr(dl, bg_model_option, dl.bg_hom3d)
    pathways = [int(p) for p in pathways_options]
    r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range
    dd_model = getattr(dl, dd_model_option, dl.dd_gauss)
    try:
        n_datasets = len(datasets)
        fit = deerlab_population_fitting(datasets,
                                model=dd_model, n_pops=n_pops,
                                bg_model=bg_model, r=r, pathways=pathways,
                                model_overrides=model_params)
        fit.n_datasets = n_datasets
        fit.n_pops = n_pops
    except Exception as e:
        print(f"Error during fitting: {e}")
        return dash.no_update, f"Error during fitting: {e}", True, True
    

    fit_store = fit_to_dict(fit,n_datasets)
    fit_store['populations'] = calc_population_fractions(fit)
    return fit_store, fit.__str__(), False, False



def fit_to_dict(fit, n_datasets):
    """
    Converts fit results to a dictionary for storage in the database.
    This version is specific for population fitting where multiple datasets are produced.
    Per-dataset fields (t, model, P_model, PUncert, background, gof) are stored as
    lists indexed by dataset order.
    """
    Prs, PUQs = determine_pop_P(fit.r, fit, fit.Pmodel, n_datasets, fit.n_pops)
    fit.P = Prs
    fit.PUncert = PUQs
    output = {}
    output['engine'] = 'DeerLab'
    output['fit_type'] = 'Population'
    output['bg_model'] = fit.bg_model.name if fit.bg_model else None
    output['dist_model'] = fit.Pmodel.name if hasattr(fit, 'Pmodel') else None
    output['n_pops'] = fit.n_pops if hasattr(fit, 'n_pops') else None
    output['pathways'] = fit.pathways[0] if hasattr(fit, 'pathways') and fit.pathways else []
    output['r'] = fit.r.tolist() if fit.r is not None else None
    output['model_description'] = fit.__str__() if fit is not None else None
    output['data'] = dl.json_dumps(fit) if fit is not None else None

    # Per-dataset fields stored as lists
    output['t'] = [fit.t[i].tolist() for i in range(n_datasets)] if fit.t is not None else None
    output['V'] = [fit.Vexp[i].tolist() for i in range(n_datasets)] if fit.Vexp is not None else None
    output['model'] = [fit.model[i].tolist() for i in range(n_datasets)] if fit.model is not None else None
    output['background'] = [fit.bg[i].tolist() for i in range(n_datasets)] if fit.bg is not None else [None] * n_datasets
    output['P_model'] = [Prs[i]['sum'].tolist() for i in range(n_datasets)]
    output['PUncert'] = [PUQs[i]['UQs']['sum'].to_dict() for i in range(n_datasets)]
    output['gof'] = [fit.stats[i] for i in range(n_datasets)]

    return output

def calc_population_fractions(fit):
    """
    Calculates the fractions of each population for each dataset and their corresponding uncertanties
    """

    n_datasets = len(fit.Vexp)
    n_pops = fit.n_pops
    output = []
    for i in range(n_datasets):
        populations = {}
        for j in range(n_pops-1):
            letter = chr(ord('A') + j)
            frac = getattr(fit, f"frac{letter}_{i+1}")
            frac_unc = getattr(fit, f"frac{letter}_{i+1}Uncert")
            ci = frac_unc.ci(95)
            unc = (ci[1] - ci[0]) / 2
            populations[letter] = {'frac': frac, 'unc': unc}
        output.append(populations)

        # Calculate the last population fraction as 1 - sum of others
        last_letter = chr(ord('A') + n_pops - 1)
        last_frac = 1 - sum(populations[chr(ord('A') + j)]['frac'] for j in range(n_pops-1))
        last_unc = np.sqrt(sum(populations[chr(ord('A') + j)]['unc']**2 for j in range(n_pops-1)))
        output[-1][last_letter] = {'frac': last_frac, 'unc': last_unc}
    return output

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
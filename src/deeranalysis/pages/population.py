import json
import copy
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback
import dash_bootstrap_components as dbc
import numpy as np
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.database import get_session, Dataset, Fit, fit_global_datasets, fit_siblings
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, plotly_deerlab,dists_stats_to_list, fit_to_dict,name_dataset_from_dict
from deeranalysis.components.fit_page_components import fit_save_download_buttons,distance_slider,adv_fit_options_parametric
import deeranalysis.components.fit_page_components as fpc

from deeranalysis.utils.deerlab_population import deerlab_population_fitting, determine_pop_P

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
layout = html.Div([
    dmc.Title("Multi-Population Global Fitting", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    
    
    dbc.Row([
        dbc.Col([
            startup_message,
            create_dataset_modal(page_id=page_id),
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
                description="These pathways will be applied to all datasets, if they are fesiable for the coresponding experiment.",
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
            # dmc.Paper([
                dmc.Accordion(
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("Advanced Fit Options"),
                                dmc.AccordionPanel(adv_fit_options_parametric(page_id))
                            ],
                            value="adv-options"
                        )
                    ]
                ),
            # ], withBorder=True, className="mb-3"),
            
            dmc.Space(h=10),
            
            fit_save_download_buttons(page_id),
            html.Div(id={'type':'fit-status','page': page_id})
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpc.plotly_deerlab_pagation(page_id=page_id),
                fpc.fit_results_tabs(
                    fpc.fit_results_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9) # dbc.col

        
    ]),
    dcc.Store(id={'type': 'fit-results-store', 'page': page_id}),
    dcc.Store(id={'type': 'fit_options', 'page': page_id}),
    # Hidden store for fit results
    
])

# ----- Clientside Callbacks for Loading States and Plot Pagination -----
clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output({"type":"run-fit-btn","page":page_id}, "loading", allow_duplicate=True),
        Input({"type":"run-fit-btn","page":page_id}, "n_clicks"),
        prevent_initial_call=True,
    )

clientside_callback(
    """
    function(page, figuresJson) {
        if (!figuresJson || !page) return dash_clientside.no_update;
        return JSON.parse(figuresJson[page - 1]);
    }
    """,
    Output({"type": "fit-plot", "page": page_id}, "figure", allow_duplicate=True),
    Input({"type": "fit-plot-pagination", "page": page_id}, "value"),
    Input({"type": "fit-plot-figures-store", "page": page_id}, "data"),
    prevent_initial_call=True,
)
clientside_callback(
    """
    function(figuresJson) {
        if (!figuresJson) return [1, 1];
        return [figuresJson.length, 1];
    }
    """,
    Output({"type": "fit-plot-pagination", "page": page_id}, "total"),
    Output({"type": "fit-plot-pagination", "page": page_id}, "value"),
    Input({"type": "fit-plot-figures-store", "page": page_id}, "data"),
    prevent_initial_call=True,
)

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




# ----- Main Fitting Callback -----


@callback(
    Output({'type': 'fit-results-store', 'page': page_id}, 'data'),
    Output({"type": "fit-plot-figures-store", "page": page_id}, 'data'),
    Output({"type":"run-fit-btn","page":page_id}, 'loading', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled'),
    Output({"type":"download-fit-btn","page":page_id}, 'disabled'),

    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit_options', 'page': page_id}, 'data'),
    prevent_initial_call=True
)
def run_fit(n_clicks, dataset_id, fit_options):

    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass

    if not dataset_id:
        return dash.no_update,dash.no_update, False, dash.no_update, dash.no_update, dash.no_update, True,True
    
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

    if triggered_id == {"page":page_id,"type":"dataset-dropdown"}:
        figures_store = []
        for ds,name in zip(datasets,dataset_names):
            fig = plotly_deerlab(fitresult=ds)
            fig.update_layout(title=f"Dataset: {name}", showlegend=True)
            figures_store.append(fig.to_json())
        return dash.no_update,figures_store, False, dash.no_update, dash.no_update, dash.no_update, True,True
    
    elif triggered_id == {"page":page_id,"type":"run-fit-btn"}:

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
                                    bg_model=bg_model, r=r, pathways=pathways)
            fit.n_datasets = n_datasets
            fit.n_pops = n_pops
        except Exception as e:
            print(f"Error during fitting: {e}")
            return dash.no_update, dash.no_update, False, f"Error during fitting: {e}", dash.no_update, dash.no_update, True, True,True
        
        # Create plots

        figures_store = []
        Ps = determine_pop_P(r,fit,dd_model,n_datasets=n_datasets,n_pops=n_pops)
        fit.P = Ps
        for i in range(n_datasets):
            plot_dict = {}
            plot_dict['t'] = fit.t[i]
            plot_dict['V'] = fit.Vexp[i]
            plot_dict['model'] = fit.model[i]
            plot_dict['P'] = Ps[i]['sum']
            plot_dict['r'] = fit.r

            fig = plotly_deerlab(fitresult=plot_dict)
            fig.update_layout(title=f"Fit Result: {dataset_names[i]}", showlegend=True)
            figures_store.append(fig.to_json())

        gof = dash.no_update
        dist_stats = dash.no_update
        fit_store = fit_to_dict(fit,n_datasets)
        return fit_store, figures_store, False, fit.__str__(), gof, dist_stats, False, False



def fit_to_dict(fit,n_datasets):
    """"
    Converts fit results to a dictionary for storage in the database. 
    This version is specific for population fitting where multiple fits are produced
    """
    fits = []
    # for
    for i in range(n_datasets):
        output = {}
        output['engine'] = 'DeerLab'
        output['fit_type'] = 'Population'

        output['t'] = fit.t[i].tolist() if fit.t is not None else None
        output['model'] = fit.model[i].tolist() if fit.model is not None else None
        output['P_model'] = fit.P[i]['sum'].tolist() if fit.P is not None else None
        output['r'] = fit.r.tolist() if fit.r is not None else None
        output['model_description'] = fit.__str__() if fit is not None else None
        output['pathways'] = fit.pathways if fit.pathways is not None else None
        output['PUncert'] = None
        fits.append(output)
    
    return 

# ----- Save and Download Callbacks -----

@callback(
    Output({'type':'fit-status','page': page_id}, 'children'),
    Input({'type':'save-fit-btn','page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id},'value'),
    State({'type':'fit-results-store','page': page_id}, 'data'),
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
    State({'type':'fit-results-store','page': page_id}, 'data'),

    prevent_initial_call=True
)
def download_fit(n_clicks, fit_store):
    if n_clicks is None or not fit_store:
        return False, dash.no_update
    
    return True, fit_store
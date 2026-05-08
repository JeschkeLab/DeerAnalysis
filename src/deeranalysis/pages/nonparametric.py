import json
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import xarray as xr
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_normal import deerlab_fitting, deerlab_background_only
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.download_modal import create_fit_download_modal
from deeranalysis.components.fit_page_components import fit_results_tabs, fit_results_tab, goodness_of_fit_tab, dist_stats_tab, L_curve_tab
from deeranalysis.components.model_edit_modal import create_model_edit_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, dists_stats_to_list, fit_to_dict,name_dataset_from_dict, build_model_data, plotly_lcurve

import deeranalysis.components.fit_page_components as fpc

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
            html.Div([
                dmc.Select(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                                id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            dmc.Space(h=10),     
            dmc.Select(
                label='Background Model',
                id='np-bg-model',
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),     
            fpc.pathway_input(page_id),
            # Small vertical space
            dmc.Space(h=10),        
            dmc.Chip('Compactness', id='np-compactness-option', value=False, checked=False),
            dmc.Space(h=10),
            fpc.distance_slider(page_id),
            dmc.Space(h=10),
            dmc.Button("Edit Dipolar Model", id={'type': 'open-model-edit-btn', 'page': page_id}, color="blue", variant='outline', className="mb-2 ms-1", leftSection=DashIconify(icon='material-symbols:edit', width=20)),
            dmc.Space(h=10),
            # dmc.Paper([
                dmc.Accordion(
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("Advanced Fit Options"),
                                dmc.AccordionPanel([
                                    dmc.Select(
                                        label='Regularization Method',
                                        description="Method for the automatic selection of the optimal regularization parameter:",
                                        id='np-regparam-method',
                                        data=regparam_options,
                                        value="bic"
                                    ),
                                    dmc.NumberInput(
                                        label="Fixed Regularization Parameter (α):",
                                        description="Set a fixed regularization parameter (overrides automatic selection)",
                                        id='np-alpha',
                                        type='text',
                                        value=None,
                                        step=0.001,
                                        allowNegative=False,
                                        className="mb-2"
                                    )
                                ])
                            ],
                            value="adv-options"
                        )
                    ]
                ),
            # ], withBorder=True, className="mb-3"),
            
            dmc.Space(h=10),
            
            dmc.Button("Run Fit", id="np-run-fit-btn", color="blue",variant='outline', className="mb-2 ms-1",leftSection=DashIconify(icon='material-symbols:play-arrow', width=20)),
            dmc.Button("Save Fit", id="np-save-fit-btn", color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:save', width=20)),
            dmc.Button("Download", id="np-download-fit-btn", color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:download', width=20)),
            html.Div(id='np-fit-status')
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id),
                fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fit_results_tab(page_id),
                    goodness_of_fit_tab(page_id),
                    dist_stats_tab(page_id),
                    L_curve_tab(page_id),
                )
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
                    
        ], width=9)
    ]),
    
    # Hidden store for fit results
    dcc.Store(id={'type':'fit-results-store','page': page_id}),
    # Hidden store for user-edited model parameter overrides
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
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('np-bg-model', 'value'),
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
    model_data = build_model_data(dataset, bg_model_name, pathways_int, distance_axis, existing_overrides)
    return True, model_data




@callback(
    Output({'type':'fit-results-store','page': page_id}, 'data', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output('np-save-fit-btn', 'disabled'),
    Output('np-download-fit-btn', 'disabled'),
    Output({'type': 'fit-plot-showpathways', 'page': page_id}, 'checked', allow_duplicate=True),

    Input('np-run-fit-btn', 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('np-bg-model', 'value'),
    State('np-compactness-option', 'checked'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State({'type': 'pathways-options', 'page': page_id}, 'value'),
    State('np-regparam-method', 'value'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    running=[(Output('np-run-fit-btn', 'loading'), True, False)],
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id, bg_model_option, compactness, distance_axis, pathways_options, regparam_method, model_params):


    if not dataset_id:
        return dash.no_update, dash.no_update, dash.no_update, True, True

        
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    mask = np.array(dataset_entry.mask) if dataset_entry.mask else None
    session.close()
    
    
    # Distance vector
    r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range
    if bg_model_option != 'none':
        bg_model = getattr(dl, bg_model_option, dl.bg_hom3d)
    else:
        bg_model = None
    # Get pathways options from checklist
    pathways = [int(p) for p in pathways_options]
    print(f"Selected pathways: {pathways_options}")
    if len(pathways) == 0:
        if bg_model is None:
            return dash.no_update, "Please select at least one pathway or a background model.", True, True, False
        try:
            fit = deerlab_background_only(
                dataset,
                bg_model=bg_model,
                model_overrides=model_params,
                mask=mask)
        except Exception as e:
            print(f"Error during background-only fitting: {e}")
            return dash.no_update, f"Error during background-only fitting: {e}", True, True, False
        fit.background= fit.model
        fit_dict = fit_to_dict(fit,background_only=True)
        fit_dict['fit_type'] = 'background'
        fit_dict['dist_stats'] = {}
        fit_dict['gof'] = fit.stats
        # fit_dict['dataset'] = dataset.to_dict()
        return fit_dict, fit.__str__(), False, False, False

    else:
        try:
            fit = deerlab_fitting(dataset,
                compactness=compactness,
                model=None,
                ROI=False,
                bg_model=bg_model,
                r=r,
                pathways=pathways,
                regparam=regparam_method,
                model_overrides=model_params,
                mask=mask)
        except Exception as e:
            print(f"Error during fitting: {e}")
            return dash.no_update, f"Error during fitting: {e}", True, True, False
        
        dist_stats = dl.diststats(r,fit.P,fit.PUncert)
        dist_stats_dict = dists_stats_to_list(*dist_stats)

        fit_dict = fit_to_dict(fit)
        fit_dict['dist_stats'] = dist_stats_dict
        fit_dict['gof'] = fit.stats
        # fit_dict['dataset'] = dataset.to_dict()
        return fit_dict, fit.__str__(), False, False, False

    if hasattr(fit,'P'):
        dist_stats = dl.diststats(r,fit.P,fit.PUncert)
        dist_stats_dict = dists_stats_to_list(*dist_stats)
    else:
        dist_stats_dict = {}

    fit_dict = fit_to_dict(fit)
    fit_dict['dist_stats'] = dist_stats_dict
    fit_dict['gof'] = fit.stats
    # fit_dict['dataset'] = dataset.to_dict()
    return fit_dict, fit.__str__(), False, False, False


@callback(
    Output('np-fit-status', 'children'),
    Input('np-save-fit-btn', 'n_clicks'),
    State( {'type': 'dataset-dropdown', 'page': page_id},'value'),
    State({'type':'fit-results-store','page': page_id}, 'data'),
    prevent_initial_call=True
)
def save_fit(n_clicks, dataset_id,dataset_store):
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
    Output({"type": "fit-dl-modal",'page': page_id}, "opened"),
    Output({"type": "fit-dl-store",'page': page_id}, "data"),
    Input('np-download-fit-btn', 'n_clicks'),
    State({'type':'fit-results-store','page': page_id}, 'data'),

    prevent_initial_call=True
)
def download_fit(n_clicks, fit_store):
    if n_clicks is None or not fit_store:
        return False, dash.no_update
    
    return True, fit_store

@callback(
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "l-curve-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
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

    dist_stats_dict = fit_dict['dist_stats']
    dist_stats_output = {
        "head": ["Statistic", "Value", "Confidence Interval (95%)"],
        "body": [
            [k, f"{v['value']:.3f}", f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]" if v['ci'] else "N/A"]
            for k, v in dist_stats_dict.items()
        ]
    }
    return gof_fig, l_curve_fig, dist_stats_output
    

    


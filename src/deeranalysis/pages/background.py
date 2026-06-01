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
from deeranalysis.components.fit_page_components import fit_results_tabs, fit_results_tab, goodness_of_fit_tab
from deeranalysis.components.model_edit_modal import create_model_edit_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, dists_stats_to_list, fit_to_dict,name_dataset_from_dict, build_model_data, plotly_lcurve

import deeranalysis.components.fit_page_components as fpc

dash.register_page(__name__)
page_id='background'


layout = html.Div([
    dmc.Title("Background-Only Fit", order=1, mb="md"),
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
                id={'type':'bg-model', 'page': page_id},
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),
            dmc.Button("Edit Dipolar Model", id={'type': 'open-model-edit-btn', 'page': page_id}, color="blue", variant='outline', className="mb-2 ms-1", leftSection=DashIconify(icon='material-symbols:edit', width=20)),
            dmc.Space(h=10),
            # dmc.Paper([
            # ], withBorder=True, className="mb-3"),
            
            dmc.Space(h=10),
            
            fpc.fit_save_download_buttons(page_id),
            html.Div(id={'type':'fit-status', 'page': page_id})
        ], width=3),
        
        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id, background_only=True),
                fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fit_results_tab(page_id),
                    goodness_of_fit_tab(page_id),
                )
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
                    
        ], width=9)
    ]),
    
    # Hidden store for fit results
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
    Output({'type': 'model-edit-modal', 'page': page_id}, 'opened'),
    Output({'type': 'model-store', 'page': page_id}, 'data'),
    Input({'type': 'open-model-edit-btn', 'page': page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type':'bg-model', 'page': page_id}, 'value'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    prevent_initial_call=True,
)
def open_model_edit_modal(n_clicks, dataset_id, bg_model_name, existing_overrides):
    if not n_clicks or not dataset_id:
        return False, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    session.close()

    model_data = build_model_data(dataset, bg_model_name, None, None, existing_overrides)
    return True, model_data

@callback(
    Output({'type': 'fit-options', 'page': page_id}, 'data'),
    Input({'type': 'bg_model', 'page': page_id}, 'value'),
    prevent_initial_call=True
)
def update_fit_options(bg_model_option):
    return {
        'bg_model': bg_model_option,
    }


@callback(
    Output({'type':'fit-results-store','page': page_id}, 'data'),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type": "save-fit-btn", "page": page_id}, 'disabled'),
    Output({"type": "download-fit-btn", "page": page_id}, 'disabled'),
    Output({'type': 'fit-plot-showpathways', 'page': page_id}, 'checked', allow_duplicate=True),

    Input({"type": "run-fit-btn", "page": page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State({'type': 'fit-options', 'page': page_id}, 'data'),
    State({'type': 'model-params-store', 'page': page_id}, 'data'),
    running=[(Output({"type": "run-fit-btn", "page": page_id}, 'loading'), True, False)],
    prevent_initial_call=True
)
def run_fit(n_clicks, dataset_id, fit_options, model_params):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass

    if not dataset_id:
        return dash.no_update, dash.no_update, dash.no_update, True, True

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    mask = np.array(dataset_entry.mask) if dataset_entry.mask else None
    session.close()

    bg_model_option = fit_options.get('bg_model', 'bg_hom3d') if fit_options else 'bg_hom3d'
    Bmodel = getattr(dl, bg_model_option, dl.bg_hom3d)

    try:
        fit = deerlab_background_only(dataset, bg_model=Bmodel, mask=mask, model_overrides=model_params)
    except Exception as e:
        print(f"Error during fitting: {e}")
        return dash.no_update, f"Error during fitting: {e}", True, True, False
    

    fit_dict = fit_to_dict(fit,background_only=True)
    fit_dict['gof'] = fit.stats
    return fit_dict, fit.__str__(), False, False, False


@callback(
    Output({'type':'fit-status', 'page': page_id}, 'children'),
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
    Input({'type': 'fit-results-store', 'page': page_id}, 'data'),
    prevent_initial_call=True
)
def update_plots_tables(fit_dict):

    if not fit_dict or 'data' not in fit_dict:
        return dash.no_update
    fit = dl.json_loads(fit_dict['data'])
    gof_fig = plotly_goodness_of_fit(fit)


    return gof_fig
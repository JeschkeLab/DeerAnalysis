import json

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import numpy as np

from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.setup_modal_desktop import get_DeerAnalysis_directory
from deeranalysis.utils.deerlab_options import  plotly_goodness_of_fit, plotly_deerlab, dists_stats_to_list, fit_to_dict,name_dataset_from_dict
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure, dataarray_from_database_entry
from deeranalysis.utils.deernet import deernet,deernet2
import deerlab as dl
dash.register_page(__name__)
import deeranalysis.components.fit_page_components as fpc

import os
page_id='deernet'

layout = html.Div([
    dmc.Title("DeerNet Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dbc.Row([
        dbc.Col([
            create_dataset_modal(page_id=page_id),
            html.Div([
                dmc.Select(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                                id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            dmc.Space(h=10),
            dmc.Select(label='Model Size',
                id='dn-model-size',
                data=[
                    {'value': '128', 'label': '128'},
                    {'value': '256', 'label': '256'},
                    {'value': '512', 'label': '512'},
                ],
                value='512',
                className="mb-3"
            ),
            # dbc.Row([
            #     dbc.Col([dmc.Select(label='Uncertainty Type',
            #         id='dn-uncertainty-type',
            #         data=[
            #             {'value': 'net', 'label': 'Network ensemble'},
            #             # {'value': 'boot', 'label': 'Bootstrap'},
            #         ],
            #         value='net',
            #         className="mb-3"
            #     )]),
            #     dbc.Col([dmc.NumberInput(
            #         label="Number of Bootstrap Samples",
            #         id="dn-bootstrap-samples",
            #         min=10,
            #         max=1000,
            #         step=10,
            #         value=100,
            #         className="mb-3",
            #         disabled=True
            #     )]),
            # ]),

            html.Br(),
            fpc.fit_save_download_buttons(page_id),
            html.Div(id='dn-fit-status')
        ], width=3),
        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id),
                fpc.fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9), # dbc.col
    ]), # dbc.row
    # Hidden store for fit results
    dcc.Store(id={'type':'fit-results-store','page': page_id}),
    dmc.Modal(id="dn-missing-models",
            title="DeerNet Models Not Found",
            opened=False,
            children=[
                dmc.Text("The DeerNet models directory was not found. Please download the models from the configuration tab."),
            ]
        )
])

@callback(
        Output('dn-missing-models', 'opened'),
        Input('url', 'pathname'),     
)
def check_deernet_models_exist(url):
    deernet_dir = os.path.join(get_DeerAnalysis_directory(), "deernet")
    if not os.path.exists(deernet_dir):
        return True

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
    Output({'type':'fit-results-store','page': page_id}, 'data'),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled'),
    Output({"type": "download-fit-btn", "page": page_id}, 'disabled'),
    Output('dn-fit-status', 'children',allow_duplicate=True),
    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('dn-model-size', 'value'),
    running=[(Output({"type":"run-fit-btn","page":page_id}, 'loading'), True, False)],
    prevent_initial_call=True,
)
def run_fit(n_clicks, dataset_id,model_size):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass

    if not dataset_id:
        # return dash.no_update, dash.no_update, dash.no_update, True, True
        return dash.no_update, True, True,None
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    dataset = dataset.assign_coords(t=dataset.t.values)
    session.close()

    if dataset_entry.exp not in ['4pDEER', '3pDEER', 'single']:
        alert = dmc.Alert(f"Dataset {dataset_entry.name} has unsupported experiment type '{dataset_entry.exp}'. Only 'single','4pDEER' and '3pDEER' are supported.!",
                          title='Error!', color="red", duration=10000,withCloseButton=True)
        return dash.no_update, True, True, alert
    model_size = int(model_size)
    deernet_folder = os.path.join(get_DeerAnalysis_directory(), "deernet", 'deernet_models')

    try:
        fit = deernet2(dataset, model_size, model_dir=deernet_folder, providor=['CPUExecutionProvider'])
    except Exception as e:
        print(f"Error running DeerNet fit: {e}")
        return dash.no_update, dash.no_update, dash.no_update, True, True

    dist_stats = dl.diststats(fit.r, fit.P, fit.PUncert)
    dist_stats_dict = dists_stats_to_list(*dist_stats)

    fit_dict = fit_to_dict(fit)
    fit_dict['dist_stats'] = dist_stats_dict
    fit_dict['gof'] = fit.stats
    # return fit_dict, gof_fig, dist_stats_output, False, False
    return fit_dict, False, False,None


@callback(
    Output('dn-fit-status', 'children'),
    Input({"type":"save-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'), 
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
    
    return dmc.Alert("Fit saved successfully!", color="green", duration=4000)


@callback(
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
    Input({'type': 'fit-results-store', 'page': page_id}, 'data'),
    prevent_initial_call=True
)
def update_plots_tables(fit_dict):

    if not fit_dict or 'data' not in fit_dict:
        return dash.no_update
    fit = dl.json_loads(fit_dict['data'])
    gof_fig = plotly_goodness_of_fit(fit)

    dist_stats_dict = fit_dict['dist_stats']
    dist_stats_output = {
        "head": ["Statistic", "Value", "Confidence Interval (95%)"],
        "body": [
            [k, f"{v['value']:.3f}", f"[{v['ci'][0]:.3f}, {v['ci'][1]:.3f}]" if v['ci'] else "N/A"]
            for k, v in dist_stats_dict.items()
        ]
    }
    return gof_fig, dist_stats_output

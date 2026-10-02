import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import numpy as np

from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.components.setup_modal_desktop import get_DeerAnalysis_directory
from deeranalysis.components.download_modal import create_fit_download_modal

from deeranalysis.utils.deerlab_options import  plotly_goodness_of_fit, plotly_deerlab, name_dataset_from_dict, plotly_dipolar_spectrum
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure, dataarray_from_database_entry
from deeranalysis.utils.job_tracking import create_job, get_job
import deerlab as dl
dash.register_page(__name__)
import deeranalysis.components.fit_page_components as fpc
from deeranalysis.components.warnings import list_of_warnings_modal
from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict

import os
page_id='deernet'

layout = html.Div([
    dmc.Title("DeerNet Fit", order=1, mb="md"),
    dmc.Divider(mb="lg"),

    dbc.Row([
        dbc.Col([
            create_dataset_modal(page_id=page_id),
            create_fit_download_modal(page_id=page_id),
            list_of_warnings_modal(page_id=page_id),
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
            html.Div(id='dn-fit-status'),
            fpc.queued_jobs_panel(page_id),
        ], width=3),
        dbc.Col([
            html.Div([
                fpc.fit_plot(page_id),
                fpc.fit_results_tabs(
                    fpc.overview_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                    fpc.dipolar_spectrum_tab(page_id),
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
    Output('dn-fit-status', 'children', allow_duplicate=True),
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('dn-model-size', 'value'),
    prevent_initial_call=True,
)
def queue_fit(n_clicks, dataset_id, model_size):
    if not dataset_id:
        fpc.notify('No Dataset', 'Please select a dataset first.', 'mdi:alert-circle-outline', 'yellow')
        return dash.no_update, dash.no_update

    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    if dataset_entry is None:
        session.close()
        return dash.no_update, dash.no_update
    label = dataset_entry.name
    if dataset_entry.exp not in ['4pDEER', '3pDEER', 'single']:
        session.close()
        alert = dmc.Alert(f"Dataset {label} has unsupported experiment type '{dataset_entry.exp}'. Only 'single','4pDEER' and '3pDEER' are supported.!",
                          title='Error!', color="red", duration=10000, withCloseButton=True)
        return alert, dash.no_update
    session.close()

    params = {'dataset_id': dataset_id, 'model_size': model_size}
    job_id = create_job(job_type='deernet_fit', page=page_id, label=label, params=params)
    fpc.notify('Fit Queued', f'Queued DeerNet fit for {label}.', 'mdi:clock-outline', 'blue')
    return dash.no_update, job_id


@callback(
    Output({'type': 'pending-auto-load', 'page': page_id}, 'data', allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    Input('dn-model-size', 'value'),
    prevent_initial_call=True,
)
def invalidate_pending_auto_load(*_args):
    """Any change to a fit parameter after queueing means the eventual result would no longer
    match what's on screen — stop watching for it so it doesn't silently auto-load."""
    return None


@callback(
    Output({'type':'fit-results-store','page': page_id}, 'data', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled', allow_duplicate=True),
    Output({"type": "download-fit-btn", "page": page_id}, 'disabled', allow_duplicate=True),
    Output('dn-model-size', 'value', allow_duplicate=True),
    Input({"type": "job-load-request", "page": page_id}, "data"),
    prevent_initial_call=True,
)
def load_queued_result(job_id):
    # Dataset dropdown is deliberately not restored — see the note in nonparametric.py's
    # load_queued_result for why (it would trigger plot_dataset and wipe the loaded result).
    no_update_4 = (dash.no_update,) * 4
    if not job_id:
        return no_update_4
    job = get_job(job_id)
    if job is None or job.status != 'done' or not job.result_data:
        return no_update_4
    p = job.params or {}
    return job.result_data, False, False, p.get('model_size')


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

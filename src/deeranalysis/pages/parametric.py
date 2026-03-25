import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback, MATCH, ctx
from dash_iconify import DashIconify

import dash_bootstrap_components as dbc
import json
import numpy as np
import deerlab as dl
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import create_subplot_figure,dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models,parametric_models, plotly_goodness_of_fit, plotly_deerlab,fit_to_dict,dists_stats_to_list,name_dataset_from_dict  
from deeranalysis.components.fit_page_components import fit_save_download_buttons,distance_slider,adv_fit_options_parametric, fit_plot,DEFAULT_FIT_RESULTS_CODE,fit_results_tab, goodness_of_fit_tab, dist_stats_tab
import deeranalysis.components.fit_page_components as fpc
from deeranalysis.utils.deerlab_normal import deerlab_fitting

import dash_mantine_components as dmc

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

dash.register_page(__name__)
page_id='parametric'

layout = html.Div([
    dmc.Title("Parametric Fit", order=1, mb="md"),
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
            dmc.Select(
                label='Distance Model',
                id='p-dist-model',
                data=parametric_models,
                value='dd_gauss'
            ),
            
            dmc.Space(h=10),     
            dmc.Select(
                label='Background Model',
                id='p-bg-model',
                data=background_models,
                value='bg_hom3d'
            ),
            dmc.Space(h=10),     
            dmc.CheckboxGroup(
                id='p-pathways-options',
                label="Pathways to include:",
                children=dmc.Group([
                    dmc.Checkbox(value='1', label='1'),
                    dmc.Checkbox(value='2', label='2'),
                    dmc.Checkbox(value='3', label='3'),
                    dmc.Checkbox(value='4', label='4'),
                    dmc.Checkbox(value='5', label='5'),
                ]),
                value=['1'], # Default selected pathways
            ),
            dmc.Space(h=10),
            fpc.distance_slider(page_id),
            html.Label("Distance Axis:"),
            dmc.Space(h=10),
            
            fit_save_download_buttons(page_id),
            html.Div(id='p-fit-status')
        ], width=3),
        
        dbc.Col([
            html.Div([
                fit_plot(page_id),
                fpc.fit_results_tabs(
                    fpc.fit_results_tab(page_id),
                    fpc.goodness_of_fit_tab(page_id),
                    fpc.dist_stats_tab(page_id),
                ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
        ], width=9) # dbc.col
        
    ]),
    
    dcc.Store(id='p-fit-results-store')
])
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
    Output('p-fit-results-store', 'data'),
    Output({"type": "fit-plot", "page": page_id}, 'figure'),
    Output({"type":"run-fit-btn","page":page_id}, 'loading', allow_duplicate=True),
    Output({"type": "fit-results-code", "page": page_id}, 'code', allow_duplicate=True),
    Output({"type": "gof-plot", "page": page_id}, 'figure', allow_duplicate=True),
    Output({"type": "dist-stats-table", "page": page_id}, 'data', allow_duplicate=True),
    Output({"type":"save-fit-btn","page":page_id}, 'disabled'),

    Input({"type":"run-fit-btn","page":page_id}, 'n_clicks'),
    Input({'type': 'dataset-dropdown', 'page': page_id}, 'value'),
    State('p-dist-model', 'value'),
    State('p-bg-model', 'value'),
    State({"type": "distance-axis", "page": page_id}, 'value'),
    State('p-pathways-options', 'value'),
    prevent_initial_call=True
)
def run_fit(n_clicks, dataset_id, dist_model_name, bg_model_option,distance_axis,pathways_options):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        triggered_id = json.loads(triggered_id)
    except (json.JSONDecodeError, TypeError):
        pass

    if not dataset_id:
        return dash.no_update,dash.no_update, False, dash.no_update, dash.no_update, dash.no_update, True
        
    session = get_session()
    dataset_entry = session.query(Dataset).filter_by(id=dataset_id).first()
    dataset = dataarray_from_database_entry(dataset_entry)
    
    deadtime = dataset.attrs.get('deadtime', 0)/1e3
    dataset = dataset.assign_coords(t=dataset.t.values + float(deadtime))
    session.close()

    
    if triggered_id == {"page":page_id,"type":"dataset-dropdown"}:
        # Just plot the data
        t = dataset.t.values + float(deadtime)    
        V = dataset.values
        V = V / np.max(np.abs(V))

        fig = plotly_deerlab(fitresult=dataset)
        fig.update_layout(title=f"Dataset: {dataset_entry.name}", showlegend=True)
        dist_stats_output = {"head": ["Statistic", "Value", "Confidence Interval (95%)"]}
        return None, fig, False, default_fit_results_code, plotly_goodness_of_fit(),dist_stats_output, True
        
    if triggered_id == {"type":"run-fit-btn","page":page_id}:
        r = np.linspace(distance_axis[0], distance_axis[1], 100) # Default range
        
        Bmodel = getattr(dl, bg_model_option, dl.bg_hom3d)
        # Select models
        Pmodel = getattr(dl,dist_model_name,dl.dd_gauss)
            
        pathways = [int(p) for p in pathways_options]
        fit = deerlab_fitting(dataset,
            compactness=False,
            model=Pmodel,
            ROI=False,
            bg_model=Bmodel,
            r=r,
            pathways=pathways,)
            
        V = fit.Vexp
        r = fit.r

        fig = plotly_deerlab(fitresult=fit)
        fig.update_layout(title=f"Fit Result: {dataset_entry.name}", showlegend=True)

        gof_fig = plotly_goodness_of_fit(fit)

        dist_stats = dl.diststats(r,fit.P,fit.PUncert)
        dist_stats_output = {"head": ["Statistic", "Value", "Confidence Interval (95%)"],
                             "body": dists_stats_to_list(*dist_stats)}
        fit_dict = fit_to_dict(fit)
        return fit_dict, fig, False, fit.__str__(), gof_fig,dist_stats_output, False


@callback(
    Output('p-fit-status', 'children'),
    Input({"type":"save-fit-btn","page":page_id}, 'n_clicks'),
    State({'type': 'dataset-dropdown', 'page': page_id}, 'value'), 
    State('p-fit-results-store', 'data'),
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

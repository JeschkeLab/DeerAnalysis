import dash
from dash import html, dcc, callback, Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import json
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from deeranalysis.utils.database import get_session, Dataset, Fit
import dash_mantine_components as dmc

from deeranalysis.components.fit_finder import fit_select
from deeranalysis.components.dataset_search_model import create_dataset_modal, search_fit_modal
from deeranalysis.utils.deerlab_options import plotly_comparison

dash.register_page(__name__)

PAGE_ID = 'comparison'
N_SLOTS = 3

layout = html.Div([
    dmc.Title("Comparison", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    create_dataset_modal(PAGE_ID),
    search_fit_modal(),
    dmc.Paper(
        dmc.Group([
            fit_select(page_id=PAGE_ID, index=str(i))
            for i in range(1, N_SLOTS + 1)
        ])
    ),
    dmc.Paper(dcc.Graph(id='comp-plot', figure=plotly_comparison(None))),
])


# @callback(
#     Output({'type': 'dataset-search-modal', 'page': MATCH}, 'opened'),
#     Input({'type': 'open-dataset-search-btn', 'page': MATCH}, 'n_clicks'),
#     prevent_initial_call=True
# )
# def open_search_modal(n_clicks):
#     return True if n_clicks else False


# @callback(
#     Output({'type': 'dataset-search-modal', 'page': MATCH}, 'opened', allow_duplicate=True),
#     Output({'type': 'dataset-dropdown', 'page': MATCH}, 'value'),
#     Input({'type': 'select-dataset-btn', 'page': MATCH}, 'n_clicks'),
#     State("dataset_table", "selectedRows"),
#     prevent_initial_call=True
# )
# def select_dataset_from_modal(n_clicks, selected_rows):
#     if n_clicks and selected_rows:
#         dataset_title = selected_rows[0].get('Title')
#         session = get_session()
#         dataset = session.query(Dataset).filter_by(name=dataset_title).first()
#         session.close()
#         return False, str(dataset.id)
#     return dash.no_update, dash.no_update


@callback(
    Output({'type': 'dataset-dropdown', 'page': PAGE_ID, 'index': ALL}, 'data'),
    Input('url', 'pathname')
)
def update_dataset_dropdowns(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return [options] * N_SLOTS


@callback(
    Output({'type': 'fit-dropdown', 'page': PAGE_ID, 'index': ALL}, 'data'),
    Input({'type': 'dataset-dropdown', 'page': PAGE_ID, 'index': ALL}, 'value'),
)
def update_fit_dropdowns(dataset_ids):
    def get_options(dataset_id):
        if not dataset_id:
            return []
        session = get_session()
        fits = session.query(Fit).filter_by(dataset_id=dataset_id).all()
        options = [{'label': fit.name, 'value': str(fit.id)} for fit in fits]
        session.close()
        return options
    return [get_options(did) for did in dataset_ids]


@callback(
    Output('comp-plot', 'figure'),
    Input({'type': 'fit-dropdown', 'page': PAGE_ID, 'index': ALL}, 'value'),
)
def compare_fits(fit_ids):
    session = get_session()
    fits = [session.query(Fit).filter_by(id=fid).first() for fid in fit_ids if fid]
    datasets = [fit.dataset for fit in fits if fit]
    session.close()

    fig = plotly_comparison([fits_and_dataset_to_dict(dataset, fit) for fit, dataset in zip(fits, datasets)])
    fig.update_layout(title=None)
    return fig


def fits_and_dataset_to_dict(dataset, fit=None):
    output = {}
    output['t'] = np.array(dataset.t, dtype=float)
    output['V'] = np.array(dataset.V, dtype=float)
    output['V'] /= output['V'].max()
    output['model'] = np.array(fit.model, dtype=float)
    output['r'] = np.array(fit.r, dtype=float)
    output['P'] = np.array(fit.P_model, dtype=float)
    return output

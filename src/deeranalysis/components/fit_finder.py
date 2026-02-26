import dash_mantine_components as dmc
from dash import html, dcc, Input, Output, State, ALL, callback, ctx
from dash_iconify import DashIconify


def fit_select(page_id, index):
    dataset_dropdown_id = {'type': 'dataset-dropdown', 'page': page_id, 'index': index}
    fit_dropdown_id = {'type': 'fit-dropdown', 'page': page_id, 'index': index}
    open_btn_id = {'type': 'open-dataset-search-btn', 'page': page_id, 'index': index}

    layout = dmc.Stack(
        [
            html.Div([
                dmc.Select(id=dataset_dropdown_id, label="Select a dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(
                    DashIconify(icon='material-symbols:search', width=20),
                    id=open_btn_id,
                    size="lg", variant="default", style={'marginTop': '25px'}
                )
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            html.Div([
                dmc.Select(id=fit_dropdown_id, label="Select a fit", style={'flex': '1 1 0'}),
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
        ],
        style={'flex': '1 1 0'}
    )

    return layout
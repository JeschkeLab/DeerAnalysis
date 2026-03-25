import dash_mantine_components as dmc
from dash import html, dcc, Input, Output, State, ALL, callback, ctx
from dash_iconify import DashIconify


def fit_select(page_id, index, color=None):
    dataset_dropdown_id = {'type': 'dataset-dropdown', 'page': page_id, 'index': index}
    fit_dropdown_id = {'type': 'fit-dropdown', 'page': page_id, 'index': index}
    open_btn_id = {'type': 'open-dataset-search-btn', 'page': page_id, 'index': index}

    accent = color or '#888888'

    slot_header = dmc.Group([
        html.Div(style={
            'width': '14px', 'height': '14px', 'borderRadius': '3px',
            'backgroundColor': accent, 'flexShrink': '0',
        }),
        dmc.Text(f"Dataset {index}", size="sm", fw=700, c=accent),
    ], gap="xs", mb=4)

    layout = dmc.Stack(
        [
            slot_header,
            html.Div([
                dmc.Select(id=dataset_dropdown_id, label="Dataset", style={'flex': '1 1 0'}),
                dmc.ActionIcon(
                    DashIconify(icon='material-symbols:search', width=20),
                    id=open_btn_id,
                    size="lg", variant="default", style={'marginTop': '25px'}
                )
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
            html.Div([
                dmc.Select(id=fit_dropdown_id, label="Fit", style={'flex': '1 1 0'}),
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),
        ],
        gap="xs",
        style={
            'flex': '1 1 0',
            'borderLeft': f'3px solid {accent}',
            'paddingLeft': '12px',
        }
    )

    return layout
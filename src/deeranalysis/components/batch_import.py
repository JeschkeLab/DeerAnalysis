import json

import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import numpy as np

from deeranalysis.components.data_viewer import data_viewer_layout, plot_upload
from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
from deeranalysis.utils.deerlab_options import experiment_type_options
from deeranalysis.utils.file_parser import group_uploaded_files, parse_file_group
import deeranalysis.components.dataset_form as df  # registers shared MATCH callbacks


def batch_import_layout():
    return html.Div([
        dcc.Store(id='batch-next-index', data=0),

        dcc.Upload(
            id='batch-upload-data',
            children=dmc.Group([
                DashIconify(icon="material-symbols:upload-file-outline", width=36, color="var(--mantine-color-blue-6)"),
                dmc.Stack([
                    dmc.Text("Drag and drop many files or click to select", size="sm", fw=500),
                    dmc.Text(".DSC/.DTA (Bruker BES3T) or .h5 (HDF5) — select all files at once", size="xs", c="dimmed"),
                ], gap=2),
            ], px="md", py="sm"),
            style={
                'width': '100%',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': 'var(--mantine-radius-sm)',
                'borderColor': 'var(--mantine-color-blue-3)',
                'backgroundColor': 'var(--mantine-color-blue-light)',
                'cursor': 'pointer',
            },
            multiple=True, className="mb-2",
        ),

        dmc.Group([
            dmc.Autocomplete(id='batch-global-project', label="Set Project for all", w=220),
            dmc.Autocomplete(id='batch-global-sample', label="Set Sample for all", w=220),
            dmc.Select(id='batch-global-exp', label="Set Experiment Type for all", data=experiment_type_options, w=200),
            dmc.Button("Apply to All", id='batch-apply-all-btn', variant='light', mt=22),
        ], align='flex-end', mt='md', mb='lg'),

        html.Div(
            id='batch-cards-grid',
            children=[],
            style={
                'display': 'grid',
                # 'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))',
                'gap': '16px',
                'width': '100%',
            },
        ),

        dmc.Group([
            dmc.Button("Save All", id='batch-save-all-btn', color='blue', size='lg', mt='lg',
                       leftSection=DashIconify(icon="mdi:content-save-all-outline", width=18)),
        ], justify='flex-end'),

        html.Div(id='batch-modals-container', children=[]),
    ])


def _card(index, title, dataset_store):
    page = f'batch-{index}'
    V = np.array(dataset_store['RealData'])
    V = (V / np.max(np.abs(V))).tolist() if np.max(np.abs(V)) > 0 else V.tolist()
    return dmc.Paper(
        [
            dcc.ConfirmDialog(
                id={'type': 'batch-remove-confirm', 'page': page},
                message="Remove this dataset from the batch?",
            ),
            dmc.Group([
                dmc.Box(
                    dmc.Sparkline(data=V, color="blue", h=60, w="100%", curveType="linear", strokeWidth=1.5),
                    style={'width': '200px', 'flexShrink': 0},
                ),
                dmc.Stack([
                    dmc.Group([
                        dmc.Text(title, size="sm", fw=500, truncate=True, style={'flex': 1}),
                        dmc.ActionIcon(
                            DashIconify(icon="mdi:arrow-expand", width=16),
                            id={'type': 'batch-expand-btn', 'page': page},
                            variant="subtle", color="gray", size="sm",
                        ),
                        dmc.ActionIcon(
                            DashIconify(icon="mdi:trash-can-outline", width=16),
                            id={'type': 'batch-remove-btn', 'page': page},
                            variant="subtle", color="red", size="sm",
                        ),
                    ], justify="space-between", wrap="nowrap", gap="xs"),
                    dmc.Group([
                        dmc.Autocomplete(id={'type': 'card-project-name', 'page': page}, placeholder="Project", size="xs", style={'flex': 1}),
                        dmc.Autocomplete(id={'type': 'card-sample-name', 'page': page}, placeholder="Sample", size="xs", style={'flex': 1}),
                        dmc.Select(
                            id={'type': 'card-exp-type', 'page': page},
                            placeholder="Experiment Type", value='4pDEER',
                            data=experiment_type_options, size="xs", style={'flex': 1},
                        ),
                    ], gap="xs", grow=True, wrap="nowrap"),
                    dmc.Text(id={'type': 'batch-tmin-warning', 'page': page}, size="xs", c="yellow.9"),
                ], gap="xs", style={'flex': 1}),
            ], align="center", wrap="nowrap", gap="md"),
        ],
        id={'type': 'batch-card', 'page': page},
        withBorder=True, p="xs", radius="md",
    )


def _error_card(index, title, message):
    page = f'batch-{index}'
    return dmc.Paper(
        [
            dcc.ConfirmDialog(
                id={'type': 'batch-remove-confirm', 'page': page},
                message="Remove this dataset from the batch?",
            ),
            dmc.Group([
                dmc.Text(title, size="sm", fw=500, truncate=True, style={'flex': 1}),
                dmc.ActionIcon(
                    DashIconify(icon="mdi:trash-can-outline", width=16),
                    id={'type': 'batch-remove-btn', 'page': page},
                    variant="subtle", color="red", size="sm",
                ),
            ], justify="space-between", wrap="nowrap", gap="xs", mb="xs"),
            dmc.Alert(message, color="red", variant="light"),
        ],
        id={'type': 'batch-card', 'page': page},
        withBorder=True, p="xs", radius="md",
    )


def _item_modal(index, title, dataset_store, delays_data, tmin):
    page = f'batch-{index}'
    metadata_children, long_values_store = build_metadata_section_datarray(dataset_store['attrs'], page=page)
    return dmc.Modal(
        id={'type': 'batch-modal', 'page': page},
        title=f"Edit Dataset — {title}",
        size="90%",
        opened=False,
        children=dmc.Grid([
            dmc.GridCol([
                metadata_long_values_model(page),
                dcc.Store(id={'type': 'dataset-store', 'page': page}, data=dataset_store),
                dcc.Store(id={'type': 'metadata-modal-store', 'page': page}, data=long_values_store),
                dmc.Autocomplete(id={'type': 'project-name', 'page': page}, label="Project Name", mb="sm"),
                dmc.Autocomplete(id={'type': 'sample-name', 'page': page}, label="Sample Name", mb="sm"),
                dmc.TextInput(id={'type': 'dataset-name', 'page': page}, label="Dataset Name", value=title, mb="sm"),
                dmc.Select(
                    label='Experiment Type:',
                    id={'type': 'experiment-type-dropdown', 'page': page},
                    value='4pDEER',
                    data=experiment_type_options,
                ),
                dmc.Title("Delays", order=4, mt="md", mb="sm"),
                html.Div(id={'type': 'tmin-warning-div', 'page': page}),
                dmc.NumberInput(
                    id={'type': 'tmin', 'page': page},
                    label='tmin (ns)', allowNegative=True, value=tmin, step=4,
                    stepHoldDelay=500, stepHoldInterval=100, decimalScale=2, mb="sm",
                ),
                dag.AgGrid(
                    id={'type': 'delays-grid', 'page': page},
                    columnDefs=[
                        {'field': 'parameter', 'headerName': 'Parameter'},
                        {'field': 'value', 'headerName': 'Value (ns)', 'editable': True},
                    ],
                    rowData=delays_data,
                    className="ag-theme-alpine",
                    style={'height': '160px', 'width': '100%'},
                ),
                dmc.Accordion(
                    children=[
                        dmc.AccordionItem(
                            value="parameters",
                            children=[
                                dmc.AccordionControl("Metadata"),
                                dmc.AccordionPanel(
                                    html.Div(
                                        id={'type': "metadata-content", 'page': page},
                                        children=metadata_children,
                                        style={"maxHeight": "24vh", "overflow": "auto"},
                                    )
                                ),
                            ],
                        )
                    ],
                    mt="md",
                ),
            ], span=4),
            dmc.GridCol([
                data_viewer_layout(page_id=page, masking_enabled=True, inital_figure=plot_upload(dataset_store)),
            ], span=8),
            # Hidden trigger — actual saving is done in bulk via the "Save All" button,
            # which fires this shared save-dataset-btn pattern for every item.
            dmc.Button(id={'type': 'save-dataset-btn', 'page': page}, style={'display': 'none'}),
        ]),
    )


def _error_message(message):
    return [dict(
        title='Error', message=message,
        icon=DashIconify(icon="material-symbols:warning"),
        color='red', duration=5000, position="top-center",
    )]


@callback(
    Output('batch-cards-grid', 'children'),
    Output('batch-modals-container', 'children'),
    Output('batch-next-index', 'data'),
    Output('notification-container', 'sendNotifications', allow_duplicate=True),
    Input('batch-upload-data', 'contents'),
    State('batch-upload-data', 'filename'),
    State('batch-cards-grid', 'children'),
    State('batch-modals-container', 'children'),
    State('batch-next-index', 'data'),
    prevent_initial_call=True,
)
def handle_batch_upload(contents_list, filenames_list, cards, modals, next_index):
    if not contents_list:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    cards = list(cards or [])
    modals = list(modals or [])
    errors = []

    for group in group_uploaded_files(filenames_list):
        group_contents = [contents_list[i] for i in group]
        group_filenames = [filenames_list[i] for i in group]
        try:
            store_data, delays_data, title, tmin = parse_file_group(group_contents, group_filenames)
        except Exception as e:
            errors.append(f"{' + '.join(group_filenames)}: {e}")
            cards.append(_error_card(next_index, ' + '.join(group_filenames), str(e)))
            next_index += 1
            continue

        delays_data, store_data = df.check_delays('4pDEER', delays_data, store_data)
        cards.append(_card(next_index, title, store_data))
        modals.append(_item_modal(next_index, title, store_data, delays_data, tmin))
        next_index += 1

    alert = _error_message("Some files could not be imported:\n" + "\n".join(errors)) if errors else dash.no_update
    return cards, modals, next_index, alert


@callback(
    Output({'type': 'batch-modal', 'page': MATCH}, 'opened'),
    Input({'type': 'batch-expand-btn', 'page': MATCH}, 'n_clicks'),
    prevent_initial_call=True,
)
def open_batch_item_modal(n_clicks):
    return bool(n_clicks)


@callback(
    Output({'type': 'metadata-value-modal', 'page': MATCH}, 'opened', allow_duplicate=True),
    Output({'type': 'metadata-value-modal-text', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'metadata-show-btn', 'page': MATCH, 'key': ALL}, 'n_clicks'),
    State({'type': 'metadata-modal-store', 'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def open_batch_metadata_modal(n_clicks_list, store_data):
    if not any(n_clicks_list or []):
        return dash.no_update, dash.no_update
    triggered_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    key = json.loads(triggered_id)['key']
    full_value = (store_data or {}).get(key, "Value not found.")
    return True, full_value


@callback(
    Output({'type': 'batch-card', 'page': MATCH}, 'style'),
    Output({'type': 'batch-tmin-warning', 'page': MATCH}, 'children'),
    Input({'type': 'dataset-store', 'page': MATCH}, 'data'),
    Input({'type': 'card-exp-type', 'page': MATCH}, 'value'),
)
def update_card_style(dataset_store, exp_type):
    if dataset_store is None:
        return {'opacity': 0.4}, None
    warning = df.check_tmin_warning(dataset_store, exp_type)
    if warning:
        style = {
            'backgroundColor': 'var(--mantine-color-yellow-0)',
            'borderColor': 'var(--mantine-color-yellow-6)',
        }
        return style, f"⚠ {warning}"
    return {}, None


# ---------------------------------------------------------------------------
# Keep the compact card fields and the modal's full-size fields in sync.
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'project-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'card-project-name', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_project_card_to_modal(value):
    return value


@callback(
    Output({'type': 'card-project-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'project-name', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_project_modal_to_card(value):
    return value


@callback(
    Output({'type': 'sample-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'card-sample-name', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_sample_card_to_modal(value):
    return value


@callback(
    Output({'type': 'card-sample-name', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'sample-name', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_sample_modal_to_card(value):
    return value


@callback(
    Output({'type': 'experiment-type-dropdown', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'card-exp-type', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_exp_card_to_modal(value):
    return value


@callback(
    Output({'type': 'card-exp-type', 'page': MATCH}, 'value', allow_duplicate=True),
    Input({'type': 'experiment-type-dropdown', 'page': MATCH}, 'value'),
    prevent_initial_call=True,
)
def sync_exp_modal_to_card(value):
    return value


@callback(
    Output({'type': 'card-project-name', 'page': MATCH}, 'data'),
    Output({'type': 'card-sample-name', 'page': MATCH}, 'data'),
    Input({'type': 'card-project-name', 'page': MATCH}, 'n_blur'),
    Input({'type': 'card-sample-name', 'page': MATCH}, 'n_blur'),
    prevent_initial_call=False,
)
def populate_card_autocomplete_options(_project_blur, _sample_blur):
    return df.get_projects_and_samples()

@callback(
    Output('batch-global-project', 'data'),
    Output('batch-global-sample', 'data'),
    Input('batch-upload-data', 'contents'),
    prevent_initial_call=False,
)
def populate_global_autocomplete_options(_contents):
    return df.get_projects_and_samples()


# ---------------------------------------------------------------------------
# Apply the global Project / Sample / Experiment fields to every dataset
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'project-name', 'page': ALL}, 'value'),
    Output({'type': 'sample-name', 'page': ALL}, 'value'),
    Output({'type': 'experiment-type-dropdown', 'page': ALL}, 'value'),
    Input('batch-apply-all-btn', 'n_clicks'),
    State('batch-global-project', 'value'),
    State('batch-global-sample', 'value'),
    State('batch-global-exp', 'value'),
    prevent_initial_call=True,
)
def apply_to_all(_, global_project, global_sample, global_exp):
    # Each ALL output must be given a list exactly as long as the number of
    # components it matched — a bare dash.no_update is rejected by Dash. The
    # patterns also match the Single Import tab (page 'upload'), so leave any
    # non-batch page untouched.
    def _column(outputs, value):
        if not value:
            return [dash.no_update] * len(outputs)
        return [
            value if str(o['id']['page']).startswith('batch-') else dash.no_update
            for o in outputs
        ]

    projects_out, samples_out, exps_out = dash.callback_context.outputs_list
    return (
        _column(projects_out, global_project),
        _column(samples_out, global_sample),
        _column(exps_out, global_exp),
    )


# ---------------------------------------------------------------------------
# Save All — fires the shared per-item save-dataset-btn callback for
# every dataset currently in the batch.
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'save-dataset-btn', 'page': ALL}, 'n_clicks'),
    Input('batch-save-all-btn', 'n_clicks'),
    State({'type': 'save-dataset-btn', 'page': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def save_all(_, current_clicks):
    return [(c or 0) + 1 for c in current_clicks]


# ---------------------------------------------------------------------------
# Remove a dataset from the batch (with confirmation)
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'batch-remove-confirm', 'page': MATCH}, 'displayed'),
    Input({'type': 'batch-remove-btn', 'page': MATCH}, 'n_clicks'),
    prevent_initial_call=True,
)
def ask_remove_confirmation(n_clicks):
    return bool(n_clicks)


@callback(
    Output('batch-cards-grid', 'children', allow_duplicate=True),
    Output('batch-modals-container', 'children', allow_duplicate=True),
    Input({'type': 'batch-remove-confirm', 'page': ALL}, 'submit_n_clicks'),
    State('batch-cards-grid', 'children'),
    State('batch-modals-container', 'children'),
    prevent_initial_call=True,
)
def remove_item(_submit_clicks, cards, modals):
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0]['value']:
        return dash.no_update, dash.no_update
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    page = json.loads(triggered_id)['page']
    cards = [c for c in cards if c['props']['id'].get('page') != page]
    modals = [m for m in modals if m['props']['id'].get('page') != page]
    return cards, modals

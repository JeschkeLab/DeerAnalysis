import dash
from dash import html, dcc, callback, Input, Output, State
import dash_mantine_components as dmc
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel
from deeranalysis.components.metadata_table import build_metadata_section_datarray, metadata_long_values_model
from deeranalysis.components.data_viewer import data_viewer_layout, plot_upload
from deeranalysis.utils.deerlab_options import experiment_type_options
import deeranalysis.components.dataset_form  # registers shared MATCH callbacks
import dash_ag_grid as dag
import json

page_id = 'logs-import'
prefix = 'logs-import-'


def create_logs_import_modal(id="logs-import-modal", title="Import from LOGs"):
    return dmc.Modal(
        title=title,
        id=id,
        size="80%",
        opened=False,
        children=[
            metadata_long_values_model(page_id),
            dcc.Store(id={"type": "metadata-modal-store", "page": page_id}, data=""),
            dcc.Store(id={'type': 'dataset-store', 'page': page_id}),
            dmc.Grid([
                dmc.GridCol([
                    dmc.Autocomplete(id={'type': 'project-name', 'page': page_id}, label="Project Name", mb="sm"),
                    dmc.Autocomplete(id={'type': 'sample-name', 'page': page_id}, label="Sample Name", mb="sm"),
                    dmc.TextInput(id={'type': 'dataset-name', 'page': page_id}, label="Dataset Name", mb="sm"),
                    dmc.Select(
                        label='Experiment Type:',
                        id={'type': 'experiment-type-dropdown', 'page': page_id},
                        value='4pDEER',
                        data=experiment_type_options,
                    ),
                    dmc.Title("Delays", order=4, mt="md", mb="sm"),
                    html.Div(id={'type': 'tmin-warning-div', 'page': page_id}),
                    dmc.NumberInput(
                        id={'type': 'tmin', 'page': page_id},
                        label='tmin (ns)',
                        allowNegative=True,
                        value=0,
                        step=4,
                        stepHoldDelay=500,
                        stepHoldInterval=100,
                        decimalScale=2,
                        mb="sm",
                    ),
                    dag.AgGrid(
                        id={'type': 'delays-grid', 'page': page_id},
                        columnDefs=[
                            {'field': 'parameter', 'headerName': 'Parameter'},
                            {'field': 'value', 'headerName': 'Value (ns)', 'editable': True},
                        ],
                        rowData=[],
                        className="ag-theme-alpine",
                        style={'height': '200px', 'width': '100%'},
                    ),
                    dmc.Accordion(
                        children=[
                            dmc.AccordionItem(
                                value="parameters",
                                children=[
                                    dmc.AccordionControl("Metadata"),
                                    dmc.AccordionPanel(
                                        children=html.Div(
                                            id={'type': "metadata-content", 'page': page_id},
                                            style={"maxHeight": "28vh", "overflow": "auto", "padding": "10px"},
                                        )
                                    ),
                                ],
                            )
                        ],
                        mt="md",
                    ),
                ], span=4),
                dmc.GridCol([
                    data_viewer_layout(page_id=page_id, correct_phase=True, masking_enabled=True),
                    dmc.Button("Add Dataset", id={'type': 'save-dataset-btn', 'page': page_id}, color="blue", mb="md"),
                ], span=8),
            ]),
        ],
        overlayProps={"color": "black", "opacity": 0.5, "blur": 0.5},
    )


def build_store_data(dataarray):
    """Build the dataset store dict from an xarray DataArray."""
    # Work with a copy so the original DataArray attrs are never mutated
    attrs = dict(dataarray.attrs)
    attrs['file_format'] = 'BES3T'
    try:
        attrs.update(parse_PulseSpel(attrs.get('PlsSPELGlbTxt', '')))
    except Exception:
        pass  # PulseSpel parsing failed; delays must be set manually

    delay_keys = ['tau1', 'tau2', 'tau3', 'tau4', 'tau5', 'tau6']
    delays = {k: attrs[k] for k in delay_keys if k in attrs}
    tmin = delays.get('deadtime', 0)

    store_data = {
        'RealData': dataarray.real.values.tolist(),
        'ImagData': dataarray.imag.values.tolist(),
        't': dataarray.X.values.tolist(),
        'attrs': attrs,
        'delays': delays,
        'tmin': tmin,
        'masked_indices': [],
    }
    metadata_children, long_values_store = build_metadata_section_datarray(dataarray)
    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]

    return store_data, metadata_children, long_values_store, delays_data, tmin


# --- Callbacks ---

@callback(
    Output({'type': 'data-viewer-plot', 'page': page_id}, 'figure', allow_duplicate=True),
    Input({'type': 'dataset-store', 'page': page_id}, 'data'),
    Input({'type': 'data-plot-correctphase', 'page': page_id}, 'checked'),
    Input({'type': 'data-masking-enabled', 'page': page_id}, 'checked'),
    prevent_initial_call=True,
)
def _build_signal_figure(dataset_store, correct_phase, masking_enabled):
    if dataset_store is None:
        return dash.no_update
    return plot_upload(dataset_store, correct_phase, masking_enabled)


@callback(
    Output({"type": "metadata-value-modal", 'page': page_id}, "opened"),
    Output({"type": "metadata-value-modal-text", 'page': page_id}, "value"),
    Input({"type": "metadata-show-btn", "key": dash.ALL}, "n_clicks"),
    State({"type": "metadata-modal-store", "page": page_id}, "data"),
    prevent_initial_call=True,
)
def open_metadata_modal(n_clicks_list, store_data):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n for n in (n_clicks_list or []) if n):
        return dash.no_update, dash.no_update

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    key = json.loads(triggered_id)["key"]
    full_value = (store_data or {}).get(key, "Value not found.")
    return True, full_value

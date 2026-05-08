import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_ag_grid as dag
import deeranalysis.utils.logs_plugin as logs
from deeranalysis.utils import eprload
from deeranalysis.components.data_viewer import data_viewer_layout, plot_upload
from deeranalysis.components.logs_import_modal import create_logs_import_modal, build_store_data, page_id as logs_import_page_id

peek_page_id = 'logs-peek'

dash.register_page(__name__, path='/logs_upload')

logsTable_column_defs = [
                {"field": "id", "headerName": "ID", "filter": False, "sortable": False,"width": 75},
                {"field": "name", "headerName": "Name", "filter": True, "sortable": True, "flex": 1},
                {"field": "owner", "headerName": "Owner", "filter": False, "sortable": True},
                {"field": "project", "headerName": "Project", "filter": False, "sortable": False,"cellRenderer": "TagsCellRenderer",},
                {"field": "sample", "headerName": "Sample", "filter": False, "sortable": False,},
                {"field": "experiment", "headerName": "Experiment", "filter": False, "sortable": False},
                {"field": "date", "headerName": "Date", "filter": False, "sortable": True, "cellDataType": "dateString", "sort": "desc"},
                {"field": "actions", "headerName": "Actions", "filter": False, "sortable": False,"width":80, "cellRenderer": "DMC_DualIconButton", "cellRendererParams": {"label": "View","leftIcon":"ph:eye","rightIcon": "ph:download-simple", "variant": "outline", "size": "xs"}},
            ]

# Layout
layout = dmc.Container([
    dcc.Store(id='logs-connected', data=False),
    dcc.Store(id='logs-datasets-store', data=[]),
    dmc.Group([
        dmc.Title("LOGS Data Import", order=1),
        dmc.ActionIcon(
            DashIconify(icon="mdi:refresh", width=20),
            id="logs-refresh-btn",
            variant="subtle",
            size="lg",
        ),
    ], mb="md"),
    dmc.Modal(id='connection-error', title="Connection Error!",withCloseButton=False,children=[
        dmc.Text("Unable to connect to the LOGs server. Please check your connection and credentials."),
        dmc.Code(id='connection-error-msg')
    ]),

    # Filter Section with Multi-Select Boxes
    dmc.Paper([
        dmc.Stack([
            dmc.Grid([
                # Persons Multi-Select
                dmc.GridCol([
                    dmc.MultiSelect(
                        id="persons-multiselect",
                        label="Persons",
                        placeholder="Select persons",
                        data=[],
                        searchable=True,
                        clearable=True,
                        leftSection=DashIconify(icon="mdi:account-multiple"),
                    )
                ], span={"base": 12, "sm": 6, "md": 4}),
                
                # Project Multi-Select
                dmc.GridCol([
                    dmc.MultiSelect(
                        id="project-multiselect",
                        label="Projects",
                        placeholder="Select projects",
                        data=[],
                        searchable=True,
                        clearable=True,
                        leftSection=DashIconify(icon="mdi:folder-multiple"),
                    )
                ], span={"base": 12, "sm": 6, "md": 4}),
                
                # Samples Multi-Select
                dmc.GridCol([
                    dmc.MultiSelect(
                        id="samples-multiselect",
                        label="Samples",
                        placeholder="Select samples",
                        data=[],
                        searchable=True,
                        clearable=True,
                        leftSection=DashIconify(icon="mdi:test-tube"),
                    )
                ], span={"base": 12, "sm": 6, "md": 4}),
                
                # Experiment Multi-Select
                dmc.GridCol([
                    dmc.MultiSelect(
                        id="experiment-multiselect",
                        label="Experiments",
                        placeholder="Select experiments",
                        data=[],
                        searchable=True,
                        clearable=True,
                        leftSection=DashIconify(icon="mdi:flask"),
                    )
                ], span={"base": 12, "sm": 6, "md": 4}),
                
                # Date Range
                dmc.GridCol([
                    dmc.DatePickerInput(
                        id="date-range-picker",
                        label="Date Range",
                        type="range",
                        placeholder="Select date range",
                        clearable=True,
                    )
                ], span={"base": 12, "sm": 6, "md": 4}),
            ], gutter="md"),
        ], gap="sm"),
    ], p="md", mb="lg", shadow="sm", withBorder=True),
    
    # AG Grid Section
    dmc.Paper([
        dmc.Title("Datasets", order=4, mb="md"),
        dmc.Box(
            [dmc.LoadingOverlay(
                id="datasets-loading-overlay",
                visible=False,
                overlayProps={"radius": "sm", "blur": 2},
                zIndex=10,

            ),
            dag.AgGrid(
                    id="datasets-grid",
                    columnDefs=logsTable_column_defs,
                    rowData=[],
                    defaultColDef={
                        "resizable": True,
                        "sortable": True,
                        "filter": True,
                    },
                    dashGridOptions={
                        "pagination": True,
                        "paginationPageSize": 20,
                        "suppressPaginationPanel": True,
                    },
                    style={"height": "600px"},
                    className="ag-theme-alpine",
                ),
            ],pos="relative",
        ),
        dmc.Group([
            dmc.Pagination(id="datasets-pagination", total=1, value=1, siblings=1),
        ], justify="center", mt="sm"),
    ], p="md", shadow="sm", withBorder=True),
    dmc.Modal(
        id='logs-peek-modal',
        title="Preview Dataset",
        size="80%",
        opened=False,
        children=[
            dcc.Store(id={'type': 'dataset-store', 'page': peek_page_id}),
            data_viewer_layout(page_id=peek_page_id, correct_phase=True),
            dmc.Group(
                [dmc.Button("Close", id="close-logs-peek-btn", variant="subtle", color="gray")],
                justify="flex-end",
                mt="md"
            ),
        ],
        overlayProps={"color": "black", "opacity": 0.5, "blur": 0.5},
    ),
    create_logs_import_modal()
],fluid=True, size="xl")

@callback(
    Output("persons-multiselect", "data"),
    Input("logs-connected", "data"),
)
def update_persons(connected):
    if not connected:
        return []
    people = logs.get_list_of_persons()
    return people

@callback(
    Output("project-multiselect", "data"),
    Input("persons-multiselect", "value"),
    State("logs-connected", "data"),
    prevent_initial_call=True
)
def update_projects(persons, connected):
    if not connected:
        return []
    projects = logs.get_list_of_projects(person_ids=persons)
    return projects

@callback(
    Output("samples-multiselect", "data"),
    Input("persons-multiselect", "value"),
    Input("project-multiselect", "value"),
    State("logs-connected", "data"),
    prevent_initial_call=True
)
def update_samples(persons, projects, connected):
    if not connected:
        return []
    samples = logs.get_list_of_samples(project_ids=projects, person_ids=persons)
    # Use name as value so client-side filtering matches the dataset's sample field
    return [{"value": s["label"], "label": s["label"]} for s in samples]

@callback(
    Output("logs-datasets-store", "data"),
    Input("logs-connected", "data"),
    Input("persons-multiselect", "value"),
    Input("project-multiselect", "value"),
)
def update_datasets_store(connected, persons, projects):
    if not connected:
        return []
    return logs.get_datasets_rowdata(person_ids=persons, project_ids=projects)


# @callback(
#     Output("datasets-grid", "rowData"),
#     Output("experiment-multiselect", "data"),
#     Input("logs-datasets-store", "data"),
#     Input("samples-multiselect", "value"),
#     Input("date-range-picker", "value"),
#     Input("experiment-multiselect", "value"),
# )
# def filter_datasets_grid(all_data, samples, date_range, experiments):
#     if not all_data:
#         experiment_options = []
#         return [], experiment_options

#     # Derive experiment options from current store data
#     experiment_options = sorted(set(r["experiment"] for r in all_data if r.get("experiment")))
#     experiment_options = [{"value": e, "label": e} for e in experiment_options]

#     filtered = all_data

#     if samples:
#         filtered = [r for r in filtered if r.get("sample") in samples]

#     if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
#         start, end = date_range[0], date_range[1]
#         filtered = [r for r in filtered if start <= (r.get("date") or "") <= end]

#     if experiments:
#         filtered = [r for r in filtered if r.get("experiment") in experiments]

#     return filtered, experiment_options

@callback(
        Output("datasets-grid", "rowData"),
        Output("datasets-pagination", "total"),
        Input("datasets-pagination", "value"),
        Input("persons-multiselect", "value"),
        Input("project-multiselect", "value"),
        Input("samples-multiselect", "value"),
        Input("experiment-multiselect", "value"),
        Input("date-range-picker", "value"),
        running=[(Output("datasets-loading-overlay", "visible"), True, False)],
)
def update_datasets_grid(page, persons, projects, samples, _experiments, date_range):
    page_size = 20
    page_number = (page or 1) - 1  # dmc.Pagination is 1-indexed, get_recent_datasets is 0-indexed
    recent_ds, count = logs.get_recent_datasets(
        person_ids=persons,
        sample_ids=samples,
        project_ids=projects,
        date_range=date_range,
        page_number=page_number, page_size=page_size)
    total_pages = max(1, -(-count // page_size))  # ceiling division
    rowData = logs.get_row_data(recent_ds)
    return rowData, total_pages

@callback(
    Output('logs-peek-modal', 'opened', allow_duplicate=True),
    Output("logs-import-modal", "opened", allow_duplicate=True),
    Input("datasets-grid", "cellRendererData"),
    State("datasets-grid", "rowData"),
    prevent_initial_call=True
)
def handle_action(data, rowData):
    if not data:
        return dash.no_update, dash.no_update
    action = data.get("value", {}).get("action")
    row_index = data.get("rowIndex")
    dataset_id = rowData[row_index].get("id")
    dataset = logs.get_dataset_by_id(dataset_id)
    custom_values = logs.get_customValues(dataset)
    if action == "left":
        file_buffers = logs.download_to_memory(dataset)
        try:
            dataarray = eprload(file_buffers)
        except ValueError as e:
            dash.set_props('notification-container', {'sendNotifications': [dict(
                title='Unsupported File Format',
                message=str(e),
                icon=DashIconify(icon='mdi:alert-circle-outline'),
                color='red', duration=6000, position='top-center',
            )]})
            return dash.no_update, dash.no_update
        store_data, _, _, _, _ = build_store_data(dataarray)
        store_data['masked_indices'] = []
        dash.set_props({'type': 'dataset-store', 'page': peek_page_id}, {"data": store_data})
        return True, False
    elif action == "right":
        file_buffers = logs.download_to_memory(dataset)
        try:
            dataarray = eprload(file_buffers)
        except ValueError as e:
            dash.set_props('notification-container', {'sendNotifications': [dict(
                title='Unsupported File Format',
                message=str(e),
                icon=DashIconify(icon='mdi:alert-circle-outline'),
                color='red', duration=6000, position='top-center',
            )]})
            return dash.no_update, dash.no_update
        store_data, metadata_children, long_values_store, delays_data, tmin = build_store_data(dataarray)

        dash.set_props({'type': 'dataset-name', 'page': logs_import_page_id}, {"value": dataset.name})
        dash.set_props({'type': 'project-name', 'page': logs_import_page_id}, {"value": [p.name for p in dataset.projects][0] if dataset.projects else ""})
        dash.set_props({'type': 'sample-name', 'page': logs_import_page_id}, {"value": custom_values.get("Sample", "")})
        dash.set_props({'type': 'dataset-store', 'page': logs_import_page_id}, {"data": store_data})
        dash.set_props({'type': 'delays-grid', 'page': logs_import_page_id}, {"rowData": delays_data})
        dash.set_props({'type': 'tmin', 'page': logs_import_page_id}, {"value": tmin})
        dash.set_props({"type": "metadata-content", "page": logs_import_page_id}, {"children": metadata_children})
        dash.set_props({"type": "metadata-modal-store", "page": logs_import_page_id}, {"data": long_values_store})
        return False, True
    return dash.no_update, dash.no_update

@callback(
    Output({'type': 'data-viewer-plot', 'page': peek_page_id}, 'figure', allow_duplicate=True),
    Input({'type': 'dataset-store', 'page': peek_page_id}, 'data'),
    Input({'type': 'data-plot-correctphase', 'page': peek_page_id}, 'checked'),
    prevent_initial_call=True
)
def update_peek_figure(dataset_store, correct_phase):
    if dataset_store is None:
        return dash.no_update
    return plot_upload(dataset_store, correct_phase)


@callback(
    Output('logs-peek-modal', 'opened', allow_duplicate=True),
    Input('close-logs-peek-btn', 'n_clicks'),
    prevent_initial_call=True
)
def close_peek_modal(_):
    return False


@callback(
        Output('connection-error','opened'),
        Output('connection-error-msg','children'),
        Output('persons-multiselect', 'disabled'),
        Output('project-multiselect', 'disabled'),
        Output('samples-multiselect', 'disabled'),
        Output('experiment-multiselect', 'disabled'),
        Output('date-range-picker', 'disabled'),
        Output('datasets-grid', 'style'),
        Output('logs-connected', 'data'),
        Input('url', 'pathname'),
        Input('logs-refresh-btn', 'n_clicks'),
)
def check_logs_connection(url, n_clicks):
    # Check the connection to logs and opens a connection warning modal upon page load or refresh
    grid_style = {"height": "600px"}
    try:
        logs.test_logs_api()
    except Exception as e:
        disabled_grid_style = {**grid_style, "pointerEvents": "none", "opacity": 0.5}
        return True, e.__str__(), True, True, True, True, True, disabled_grid_style, False
    else:
        return False, "", False, False, False, False, False, grid_style, True
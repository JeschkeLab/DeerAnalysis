import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_ag_grid as dag
import deeranalysis.utils.logs_plugin as logs
from deeranalysis.utils import eprload
from deeranalysis.components.viewer_modals import create_viewer_modal
from deeranalysis.components.logs_import_modal import create_logs_import_modal

dash.register_page(__name__, path='/logs_upload')

logsTable_column_defs = [
                {"field": "id", "headerName": "ID", "filter": True, "sortable": True, "width": 100},
                {"field": "name", "headerName": "Name", "filter": True, "sortable": True, "flex": 1},
                {"field": "owner", "headerName": "Owner", "filter": True, "sortable": True},
                {"field": "project", "headerName": "Project", "filter": False, "sortable": False,"cellRenderer": "TagsCellRenderer",},
                {"field": "sample", "headerName": "Sample", "filter": True, "sortable": True,},
                {"field": "experiment", "headerName": "Experiment", "filter": True, "sortable": True},
                {"field": "date", "headerName": "Date", "filter": True, "sortable": True, "cellDataType": "dateString"},
                {"field": "actions", "headerName": "Actions", "filter": False, "sortable": False,"width":80, "cellRenderer": "DMC_DualIconButton", "cellRendererParams": {"label": "View","leftIcon":"ph:eye","rightIcon": "ph:download-simple", "variant": "outline", "size": "xs"}},
            ]

# Layout
layout = dmc.Container([
    dmc.Title("LOGS Data Upload", order=1, mb="md"),
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
                "paginationPageSizeSelector": [10, 20, 50, 100],
            },
            style={"height": "600px"},
            className="ag-theme-alpine",
        ),
    ], p="md", shadow="sm", withBorder=True),
    create_viewer_modal('viewer-modal'),
    create_logs_import_modal()
],fluid=True, size="xl")

@callback(
    Output("persons-multiselect", "data"),
    Input("persons-multiselect", "id")  # Dummy input to trigger callback on page load
)
def update_persons(id):
    # Fetch persons from LOGS and return as options for MultiSelect
    # Example: return [{"value": p.id, "label": p.name} for p in logs.get_persons()]
    people = logs.get_list_of_persons()
    return people

@callback(
    Output("project-multiselect", "data"),
    Input("persons-multiselect", "value"),
    prevent_initial_call=True
)
def update_projects(persons):
    # Fetch projects from LOGS and return as options for MultiSelect
    projects = logs.get_list_of_projects(person_ids=persons)
    return projects

@callback(
    Output("samples-multiselect", "data"),
    Input("persons-multiselect", "value"),
    Input("project-multiselect", "value"),
    prevent_initial_call=True
)
def update_samples(persons, projects):
    # Fetch samples from LOGS and return as options for MultiSelect
    samples = logs.get_list_of_samples(project_ids=projects, person_ids=persons)
    return samples

@callback(
    Output("datasets-grid", "rowData"),
    Input("project-multiselect", "value"),
    Input("samples-multiselect", "value"),
    prevent_initial_call=True
)
def update_datasets_grid(projects,samples):
    # Fetch datasets based on selected projects and samples, then update AG Grid
    if len(samples) == 0:
        return dash.no_update
    datasets = logs.get_list_of_datasets(project_ids=projects, sample_ids=samples)
    # Convert datasets to rowData format for AG Grid
    rowData = []
    for ds in datasets:
        custom_values = logs.get_customValues(ds)
        rowData.append({
            "id": ds.id,
            "name": ds.name,
            "owner": ds.owner.name if ds.owner else "None",
            # "project": ds.projects if ds.projects else "None",
            "projects": [p.name for p in ds.projects] if ds.projects else "None",
            "sample": custom_values.get("Sample", ""),
            "experiment":custom_values.get("Experiment", ""),
            "date":ds.creationDate.strftime("%Y-%m-%d") if ds.creationDate else ""

        })
    return rowData


@callback(
    Output("viewer-modal", "opened",allow_duplicate=True),
    Output("viewer-modal-figure", "figure"),
    Output("logs-import-modal", "opened",allow_duplicate=True),
    Input("datasets-grid", "cellRendererData"),
    State("datasets-grid", "rowData"),
    State("viewer-modal-figure", "figure"),
    prevent_initial_call=True
)
def handle_action(data,rowData,current_figure):
    if not data:
        return dash.no_update
    action = data.get("value", {}).get("action")
    row = data.get("rowData", {})
    row_index = data.get("rowIndex")
    dataset_id = rowData[row_index].get("id")
    dataset = logs.get_dataset_by_id(dataset_id)
    custom_values = logs.get_customValues(dataset)
    if action == "left":
        # Open viewer modal and populate with dataset details
        
        tracks = logs.get_tracks_from_dataset(dataset)
        current_figure.update(logs.dash_plot_update_from_tracks(tracks))
        return True, current_figure, False
    elif action == "right":

        file_buffers = logs.download_to_memory(dataset)
        dataarray = eprload(file_buffers)
        dash.set_props("logs-import"+"dataset-name", {"value": dataset.name})
        dash.set_props("logs-import"+"project-name", {"value": [p.name for p in dataset.projects][0] if dataset.projects else ""})
        dash.set_props("logs-import"+"sample-name", {"value": custom_values.get("Sample", "")})
        return dash.no_update,dash.no_update,True

@callback(
        Output('connection-error','opened'),
        Output('connection-error-msg','children'),
        Input('url', 'pathname')
)
def check_logs_connection(url):
    # Check the connection to logs and opens a connection warning modal upon page load
    try:
        logs.test_logs_api()
    except Exception as e:
        return True, e.__str__()
    else:
        return False, ""
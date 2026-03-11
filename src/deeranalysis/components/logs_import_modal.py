import dash
from dash import html, dcc, callback, Input, Output, State
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset
import dash_ag_grid as dag  



def dataset_key_paper(id=""):
    return dmc.Container(
        [
            dmc.Paper([
                dmc.Autocomplete(id=id+"project-name", placeholder="Sample Name",label='Sample Name', className="mb-2"),
                dmc.Autocomplete(id=id+"sample-name", placeholder="Project Name",label='Project Name', className="mb-2"),
                dmc.TextInput(id=id+"dataset-name", placeholder="Dataset Name",label='Dataset Name', className="mb-2"),
                dmc.Select(id=id+'experiment-type-dropdown',data=[
                        {'label': '3-pulse', 'value': '3pDEER'},
                        {'label': '4-pulse', 'value': '4pDEER'},
                        {'label': '5-pulse', 'value': '5pDEER'},
                        {'label': 'RIDME', 'value': '5pRIDME'},
                    ],
                    label="Experiment Type:",
                    value='4pulse',
                    placeholder="Select experiment type(s)")
            ]),
            dmc.Paper([
                html.H4("Delays:", className="mt-2"),
                dag.AgGrid(
                id=id+'delays-grid',
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value (ns)', 'editable': True}
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '200px', 'width': '100%'}),
                html.H4("Additional Parameters", className="mt-3"),
                dag.AgGrid(
                id=id+'data-parameters-grid',
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value'}
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '300px', 'width': '100%'})
        ]
    )])

def create_logs_import_modal(id="logs-import-modal", title="Import Logs"):
    """
    Creates a reusable modal component for importing logs datasets.
    On the left there is a section for setting the sample name, project name and dataset name. Below this is the experimenty type, delays and parameters. On the right is a dataviewer.

    Parameters
    ----------
    id : str, optional
        _description_, by default "logs-import-modal"
    title : str, optional
        _description_, by default "Import Logs"

    Returns
    -------
    _type_
        _description_
    """

    return dmc.Modal(
        title=title,
        id=id,
        size="80%",
        opened=False,  # Control visibility with a callback
        children = dmc.Grid(
            [dmc.GridCol(dataset_key_paper('logs-import'), span=6),
            dmc.GridCol(
                [dcc.Graph(id="logs-import-preview-graph", figure={"data": [], "layout": {"title": "Dataset Preview"}})], span=6)
            ]
        ),
        overlayProps={"color": "black", "opacity": 0.5, "blur": 0.5},
    )   
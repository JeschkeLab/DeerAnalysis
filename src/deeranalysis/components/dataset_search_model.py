from dash import html, dcc, callback, Input, Output, State
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset
import dash_ag_grid as dag  

def create_dataset_AGgrid(id="datasets_grid"):
    columnDefs = [
        {'field': 'Title',
        'filter': 'agTextColumnFilter',
    },
        {'field': 'Project',
        'filter': 'agTextColumnFilter',
    },
        {'field': 'Sample',
        'filter': 'agTextColumnFilter',
    },
        {'field': 'Experiment',
        'filter': 'agTextColumnFilter',
    },

    ]
    grid = html.Div(dag.AgGrid(
        id=id,
        columnDefs=columnDefs,
        defaultColDef={"sortable": True, "resizable": True},
        rowData=[{'Title': 'Loading...'}],
        className="ag-theme-alpine",
        columnSize="sizeToFit",
        style={"height": "100%", "width": "100%"},
        dashGridOptions={"rowSelection": "single"},
        ),style={"height": "50vh", "marginBottom": "10px"})
    return grid

def create_dataset_modal(id="dataset-search-modal"):
    return dmc.Modal(
        title="Search Datasets",
        id=id,
        size="80%",
        opened=False,  # Add this - control visibility with a callback
        children=[
            dmc.TextInput(
                id="dataset-search-input",
                placeholder="Search for a dataset...",
                className="mb-2"
            ),
            create_dataset_AGgrid("dataset_table"),
            dmc.Group(
                [dmc.Button("Select Dataset", id="select-dataset-btn")],
                justify="flex-end",
                className="mt-2"
            ),
        ],
        
    )

@callback(
    Output("dataset_table", "rowData"),
    Input("dataset-search-input", "value"),
    prevent_initial_call=False
)
def update_dataset_table(search_value=''):
    session = get_session()
    datasets = session.query(Dataset).all()
    
    # if search_value:
    #     datasets = datasets.filter(Dataset.name.ilike(f"%{search_value}%"))
    
    session.close()
    
    data = []
    for ds in datasets:
        data.append({
            'Title': ds.name,
            'Project': ds.project,
            'Sample': ds.sample,
            'Experiment': ds.exp,
            # '# Fits': ds.n_fits,
            # 'Fit': 'Fit',
            # 'Compare': 'Compare',
        })
    
    return data


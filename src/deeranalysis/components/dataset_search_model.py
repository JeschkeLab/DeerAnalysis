import dash
from dash import html, dcc, callback, Input, Output, State, MATCH
import dash_mantine_components as dmc
from deeranalysis.utils.database import get_session, Dataset, Fit
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

def create_dataset_modal(page_id):
    return html.Div([
        dmc.Modal(
            title="Search Datasets",
            id={'type': 'dataset-search-modal', 'page': page_id},
            size="80%",
            opened=False,
            children=[
                dmc.TextInput(
                    id="dataset-search-input",
                    placeholder="Search for a dataset...",
                    className="mb-2"
                ),
                create_dataset_AGgrid("dataset_table"),
                dmc.Group(
                    [dmc.Button("Select Dataset", id={'type': 'select-dataset-btn', 'page': page_id})],
                    justify="flex-end",
                    className="mt-2"
                ),
            ],
        )
    ])

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

@callback(
    Output({'type': 'dataset-search-modal', 'page': MATCH}, 'opened'),
    Input({'type': 'open-dataset-search-btn', 'page': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def open_search_modal(n_clicks):
    return True if n_clicks else False


@callback(
    Output({'type': 'dataset-search-modal', 'page': MATCH}, 'opened', allow_duplicate=True),
    Output({'type': 'dataset-dropdown', 'page': MATCH}, 'value'),
    Input({'type': 'select-dataset-btn', 'page': MATCH}, 'n_clicks'),
    State("dataset_table", "selectedRows"),
    prevent_initial_call=True
)
def select_dataset_from_modal(n_clicks, selected_rows):
    if n_clicks and selected_rows:
        dataset_title = selected_rows[0].get('Title')
        session = get_session()
        dataset = session.query(Dataset).filter_by(name=dataset_title).first()
        session.close()
        return False, str(dataset.id)
    return dash.no_update, dash.no_update



def search_fit_modal(id="fit-search-modal"):
    return dmc.Modal(
        title="Search Fits",
        id=id,
        size="80%",
        opened=False,  # Add this - control visibility with a callback
        children=[
            dcc.Store(id=id+"-dataset_store"),  # tracks which component triggered the modal
            dcc.Store(id=id+"-opener"),
            dmc.TextInput(
                id="fit-search-search-input",
                placeholder="Search for a dataset...",
                className="mb-2"
            ),
            create_dataset_AGgrid("fit-search_table"),
            dmc.Group(
                [dmc.Button("Select Dataset", id="select-fit-btn")],
                justify="flex-end",
                className="mt-2"
            ),
        ],
        
    )

@callback(
    Output("fit-search_table", "rowData"),
    Input("fit-search-search-input", "value"),
    State("fit-search-modal-dataset_store", "data"),
    prevent_initial_call=False
)
def update_fit_search_table(search_value='',dataset_id=None):
    session = get_session()
    fits = session.query(Fit).filter_by(dataset_id=dataset_id).all()
    
    # if search_value:
    #     datasets = datasets.filter(Dataset.name.ilike(f"%{search_value}%"))
    
    session.close()
    
    data = []
    for f in fits:
        data.append({
            'Title': f.name,

            # '# Fits': ds.n_fits,
            # 'Fit': 'Fit',
            # 'Compare': 'Compare',
        })
    
    return data
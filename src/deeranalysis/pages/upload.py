import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import json
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils.eprload import bes3t_eprload
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel
import numpy as np
import plotly.graph_objs as go
import xarray as xr
import dash_ag_grid as dag  
import dash_mantine_components as dmc
from sqlalchemy.orm import Session

dash.register_page(__name__)


layout = html.Div([
    html.H1("Upload Dataset"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H4("Upload New Dataset"),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files: .DSC/.DTA, .h5, .csv\n'),
                    html.Small('(Select both .DSC and .DTA at the same time)')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '30px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                multiple=True
            ),
            dcc.Store(id='dataset-store'),
            dmc.Autocomplete(id="project-name", placeholder="Sample Name", className="mb-2"),
            dmc.Autocomplete(id="sample-name", placeholder="Project Name", className="mb-2"),
            dbc.Input(id="dataset-name", placeholder="Dataset Name", type="text", className="mb-2"),
            
            html.Div(id='upload-status'),
            dbc.Row([
                dbc.Col(html.H4("Experiment Type:", className="mt-2")),
                dbc.Col(dcc.Dropdown(
                    id='experiment-type-dropdown',
                    options=[
                        {'label': '3-pulse', 'value': '3pDEER'},
                        {'label': '4-pulse', 'value': '4pDEER'},
                        {'label': '5-pulse', 'value': '5pDEER'},
                        {'label': 'RIDME', 'value': '5pRIDME'},
                    ],
                    value='4pulse',
                    multi=False,
                    placeholder="Select experiment type(s)"
                ))]
            ),
            
            html.H4("Delays", className="mt-3"),
            dag.AgGrid(
                id='delays-grid',
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value (ns)', 'editable': True}
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '200px', 'width': '100%'}
            ),
            
            html.H4("Parameters", className="mt-3"),
            dag.AgGrid(
                id='data-parameters-grid',
                columnDefs=[
                    {'field': 'parameter', 'headerName': 'Parameter'},
                    {'field': 'value', 'headerName': 'Value'}
                ],
                rowData=[],
                className="ag-theme-alpine",
                style={'height': '300px', 'width': '100%'}
            )
        ], width=4),
        dbc.Col([
            html.H4("Data Viewer"),
            dcc.Graph(id='data-viewer-plot',
                      style={'height': '500px'}),
            dbc.Button("Add Dataset", id="save-dataset-btn", color="primary", className="mb-3"),
        ], width=8),
    ]),
])

@callback(
    Output('upload-status', 'children'),
    Output('dataset-store', 'data'),
    Output('data-parameters-grid', 'rowData'),
    Output('delays-grid', 'rowData'),
    Output('data-viewer-plot', 'figure'),
    Output('dataset-name', 'value'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True)
def handle_file_upload(contents_list, filenames_list):
    """ Uploads a dataset and extracts metadata

    Suported file types: .DSC (Bruker BES3t), 'h5' (HDF5), '.csv' (Comma-separated values)
    """

    if contents_list is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # Ensure we're working with lists
    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames_list = [filenames_list]
    
    # Only permit multiple files for .DSC + .DTA
    if len(contents_list) > 2:
        return html.Div([
            html.P("Please upload only one dataset at a time. For Bruker BES3T files, upload both the .DSC and .DTA files together.")
        ]), dash.no_update, dash.no_update, dash.no_update, dash.no_update
    elif len(contents_list) == 2:
        if not (filenames_list[0].endswith('.DSC') and filenames_list[1].endswith('.DTA')) and not (filenames_list[1].endswith('.DSC') and filenames_list[0].endswith('.DTA')):
            return html.Div([
                html.P("When uploading two files, please ensure they are the .DSC and .DTA files from Bruker BES3T.")
            ]), dash.no_update, dash.no_update, dash.no_update, dash.no_update
        file_format= 'BES3T'
    else:
        if filenames_list[0].endswith('.DSC'):
            return html.Div([
                html.P("Please upload both the .DSC and .DTA files from Bruker BES3T together.")
            ]), dash.no_update,dash.no_update, dash.no_update, dash.no_update
        elif filenames_list[0].endswith('.h5'):
            file_format = 'hdf5'
        elif filenames_list[0].endswith('.csv'):
            file_format = 'csv'
        else:
            return html.Div([
                html.P("Unsupported file type. Please upload .DSC/.DTA (Bruker BES3T), .h5 (HDF5), or .csv files.")
            ]), dash.no_update,dash.no_update, dash.no_update, dash.no_update
        
    try:
        if file_format == 'BES3T':
            # Identify which content is which
            if filenames_list[0].endswith('.DSC'):
                dsc_content = contents_list[0]
                dta_content = contents_list[1]
            else:
                dsc_content = contents_list[1]
                dta_content = contents_list[0]
            
            # Decode and parse the files
            dsc_decoded = base64.b64decode(dsc_content.split(',')[1])
            dta_decoded = base64.b64decode(dta_content.split(',')[1])
            dataarray = bes3t_eprload(DSC=dsc_decoded,DTA=dta_decoded)
            
            attribute_data =get_attributes_dict(dataarray)

            # Extract delays from pulsespel
            dataarray.attrs.update({'file_format': 'BES3T'})
            dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt','')))

            delays = get_delays_dict(dataarray)
            deadtime = delays.get('deadtime', 0)
            # dataarray.X = dataarray.X + deadtime  # Adjust time axis for deadtime
            
            # Show plot
            figure = update_data_viewer(dataarray,deadtime)
        else:
            return html.Div([
                html.P("Unsupported file type. Please upload .DSC/.DTA (Bruker BES3T), .h5 (HDF5), or .csv files.")
            ]), dash.no_update,dash.no_update, dash.no_update, dash.no_update
    except Exception as e:
        return html.Div([
            html.P(f"Error processing files: {str(e)}")
        ]), dash.no_update,dash.no_update, dash.no_update, dash.no_update
    
    
    # save dataarray to dcc.Store for later use
    store_data = {}
    store_data['RealData'] = dataarray.real.values.tolist()
    store_data['ImagData'] = dataarray.imag.values.tolist()
    store_data['t'] = dataarray.X.values.tolist()
    store_data['attrs'] = dataarray.attrs
    store_data['delays'] = delays
    store_data['deadtime'] = deadtime


    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]
    
    return html.Div([
        html.P(f"Successfully uploaded {', '.join(filenames_list)} as {file_format} format.")
    ]), store_data, attribute_data, delays_data, figure, dataarray.attrs.get('title', '')


def update_data_viewer(dataset,deadtime=0):
    """ Updates the data viewer plot with the uploaded data """
    # 

    # figure = go.Figure()

    # convert t to microseconds 
    t =dataset.X.values+deadtime
    V = dataset.values
    title_text = dataset.attrs.get('title', 'Uploaded Data')
    figure = {
        'data': [
            go.Scatter(x=t, y=V.real, mode='lines', name='Re. Part'),
            go.Scatter(x=t, y=V.imag, mode='lines', name='Im. Part'),
        ],
        'layout': go.Layout(
            title=title_text,
            xaxis_title='Time (us)',
            yaxis_title='Signal (a.u.)',
            template='plotly_white'
        )
    }
    
    return figure

def get_delays_dict(dataarray: xr.DataArray):
    """ Extracts delay parameters from the dataset attributes """
    # Possible delay keys in the attributes
    delay_keys = ['tau1', 'tau2', 'tau3', 'tau4', 'tau5', 'tau6']
    delays = {}
    for key in delay_keys:
        if key in dataarray.attrs:
            delays[key] = dataarray.attrs[key]
    return delays

def get_attributes_dict(dataarray: xr.DataArray):
    """ Updates the parameters table with extracted metadata """
    # Dataset attributes to search for
    search_attrs = [
    'B','reptime', 'freq', 'tau1', 'tau2', 'nshots', 'nscans']
    
    
    data = []
    for key, value in dataarray.attrs.items():
        if key in search_attrs:
            data.append({'parameter': key, 'value': str(value)})
    return data

@callback(
        Input('save-dataset-btn', 'n_clicks'),
        State('project-name', 'value'),
        State('sample-name', 'value'),
        State('dataset-name', 'value'),
        State('dataset-store', 'data'),
        State('experiment-type-dropdown', 'value'),
        prevent_initial_call=True)
def save_dataset(n_clicks, project_name, sample_name, dataset_name,dataset_store, experiment_type):
    """ Saves the uploaded dataset to the database """
    if n_clicks is None:
        return dash.no_update
    if not project_name or not sample_name or not dataset_name:
        return dash.no_update
        
    session = get_session()

    new_dataset = Dataset(
        name=dataset_name,
        project=project_name,
        sample=sample_name,
        t=dataset_store['t'],
        V=dataset_store['RealData'],
        V_im=dataset_store['ImagData'],
        exp=experiment_type,
        delays={},
        meta=dataset_store['attrs']
    )
    session.add(new_dataset)
    session.commit()
    session.close()

@callback(
    Output('project-name', 'data'),
    Output('sample-name', 'data'),
    Input('project-name', 'n_clicks'),
    prevent_initial_call=False)
def update_samples_and_projects(n_clicks):
    session = get_session()
    datasets = session.query(Dataset).all()
    session.close()
    
    projects = list(set(ds.project for ds in datasets))
    samples = list(set(ds.sample for ds in datasets))
    return projects, samples
    

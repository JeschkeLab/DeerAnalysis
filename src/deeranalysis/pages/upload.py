import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import json
from deeranalysis.utils.database import get_session, Dataset
from deeranalysis.utils.eprload import bes3t_eprload
import numpy as np
import plotly.graph_objs as go
import xarray as xr


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
            dbc.Input(id="project-name", placeholder="Sample Name", type="text", className="mb-2"),
            dbc.Input(id="sample-name", placeholder="Project Name", type="text", className="mb-2"),
            dbc.Input(id="dataset-name", placeholder="Dataset Name", type="text", className="mb-2"),
            
            html.Div(id='upload-status'),
            html.H4("Parmeters"),
        dbc.Col([
            dash_table.DataTable(
                id='data-parameters-table',
                columns=[
                    {'name': 'Parameter', 'id': 'parameter'},
                    {'name': 'Value', 'id': 'value'}
                ],
                data=[],
                style_table={'overflowX': 'auto',
                             'width': '100%'},
                style_cell={'textAlign': 'left'},
            )
        ], width=8)
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
    Output('data-parameters-table', 'data'),
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
        return dash.no_update, dash.no_update, dash.no_update
    
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
            figure = update_data_viewer(dataarray)
            attribute_data =get_attributes_dict(dataarray)



            
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


    return html.Div([
        html.P(f"Successfully uploaded {', '.join(filenames_list)} as {file_format} format.")
    ]), store_data,attribute_data, figure, dataarray.attrs.get('title', '')


def update_data_viewer(dataset):
    """ Updates the data viewer plot with the uploaded data """
    # 

    # figure = go.Figure()

    # convert t to microseconds 
    t =dataset.X.values
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
        prevent_initial_call=True)
def save_dataset(n_clicks, project_name, sample_name, dataset_name,dataset_store):
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
        delays={},
        meta=dataset_store['attrs']
    )
    session.add(new_dataset)
    session.commit()
    session.close()
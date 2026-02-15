from LOGS import LOGS
from LOGS.Entities import DatasetRequestParameter,PersonRequestParameter, ProjectRequestParameter, InventoryItemRequestParameter, SampleRequestParameter
import urllib3
from io import BytesIO
from zipfile import ZipFile

url = r'https://eprlogs.ethz.ch/jeschke/'
apiKey='Nr6rxTTYXBH2x488X2mi67TfWGp1bVABo3Yo8EBMQAY+HZzmoZecYuJTuMUFDEQQ'
urllib3.disable_warnings() 

def test_logs_api():
    
    try:
        logs = LOGS(url, apiKey,verify= False)
    except Exception as e:
        raise Exception(f"Failed to connect to LOGS API: {e}")

def convert_to_dict(results):
    results_dict = {}
    for r in results:
        results_dict[r.id] = r.name  
    return results_dict

def convert_to_list_of_dicts(results):
    results_list = []
    for r in results:
        results_list.append({"value": str(r.id), "label": r.name})
    return results_list

def get_list_of_persons():
    logs = LOGS(url, apiKey,verify= False)
    persons = logs.persons()

    return convert_to_list_of_dicts(persons)


def get_list_of_projects(person_ids=None):
    logs = LOGS(url, apiKey,verify= False)
    if person_ids:
        if not isinstance(person_ids, list):
            person_ids = [person_ids]
        # Make all ids ints
        person_ids = [int(pid) for pid in person_ids]
        projects = logs.projects(
            ProjectRequestParameter(personIds=person_ids)
        )
    else:
        projects = logs.projects()

    return convert_to_list_of_dicts(projects)

def get_list_of_samples(person_ids=None, project_ids=None):
    logs = LOGS(url, apiKey,verify= False)
    
    if person_ids:
        if not isinstance(person_ids, list):
            person_ids = [person_ids]
        person_ids = [int(pid) for pid in person_ids]
    if project_ids:
        if not isinstance(project_ids, list):
            project_ids = [project_ids]
        project_ids = [int(pid) for pid in project_ids]

    samples = logs.samples(
        SampleRequestParameter(projectIds=project_ids)
    )

    return convert_to_list_of_dicts(samples)


def get_list_of_datasets(person_ids=None, project_ids=None, sample_ids=None):
    logs = LOGS(url, apiKey,verify= False)
    if person_ids:
        if not isinstance(person_ids, list):
            person_ids = [person_ids]
        person_ids = [int(pid) for pid in person_ids]
    if project_ids:
        if not isinstance(project_ids, list):
            project_ids = [project_ids]
        project_ids = [int(pid) for pid in project_ids]
    if sample_ids:
        if not isinstance(sample_ids, list):
            sample_ids = [sample_ids]
        sample_ids = [int(sid) for sid in sample_ids]
    datasets = logs.datasets(DatasetRequestParameter(
                                projectIds=project_ids,
                                )    
                             )
    return datasets

def get_dataset_by_id(dataset_id):
    logs = LOGS(url, apiKey,verify= False)
    dataset = logs.dataset(dataset_id)
    return dataset
    
def get_list_of_experiments():
    logs = LOGS(url, apiKey,verify= False)
    experiments = logs.experiments()
    return convert_to_list_of_dicts(experiments)

def get_customValues(dataset):
    custom_values = {}
    for cValue in dataset.customValues.toDict()[0]['content']:
        if 'value' in cValue and not isinstance(cValue['value'], list):
            if isinstance(cValue['value'], dict) and 'name' in cValue['value']:
                custom_values[cValue['name']] = cValue['value']['name']
            else:                
                custom_values[cValue['name']] = cValue['value']
        elif 'value' in cValue and isinstance(cValue['value'], list):
            custom_values[cValue['name']] = [v['name'] for v in cValue['value']]
        else:
            custom_values[cValue['name']] = None
    return custom_values

def get_tracks_from_dataset(dataset, verbose=False):
    dataset.fetchInfo()
    n_tracks = len(dataset.tracks)
    if verbose:
        print(f"Number of tracks in dataset '{dataset.name}': {n_tracks}")
    traces = []
    for track in dataset.tracks:
        track.fetchDatatracks()
        if verbose:
            print(f"Track: {track.id} - {track.name}- {track.type}")
        settings = track.settings.toDict()
        datatracks = track.datatracks
        if 'XY_complex' == track.type:
            re = datatracks.re.data
            im = datatracks.im.data
        elif 'XY_real' == track.type:
            re = datatracks.re.data
            im = [0] * len(re)
        else:
            raise ValueError(f"Unsupported track type: {track.type}")
        x = datatracks.x.data
        traces.append({'X':x, 'Y':re+1j*im,
                    'axisLabels':settings.get('axisLabels', {}),
                    'axisUnits':settings.get('axisUnits', {})})
    return traces


def dash_plot_update_from_tracks(tracks):
    import plotly.graph_objs as go

    current_fig={}
    current_fig['data'] = []

    for track in tracks:
        trace_re = go.Scatter(x=track['X'], y=track['Y'].real, mode='lines', name='Re', marker=dict(size=5, color='black'))
        trace_im = go.Scatter(x=track['X'], y=track['Y'].imag, mode='lines', name='Im', marker=dict(size=5, color='red'))
        current_fig['data'].append(trace_re)
        current_fig['data'].append(trace_im)
    return current_fig
    

def download_to_memory(dataset, verbose=False):

    """
    Dowloads the dataset's zip file to memory and extracts its contents into a dictionary of file buffers.

    Parameters:
    -----------
    dataset: LOGS.Entities.Dataset
        The dataset to download.
    verbose: bool
        If True, prints additional information about the download process.
    Returns:
    --------
    dict
        A dictionary where keys are filenames and values are BytesIO buffers containing the file data.
    """
    from LOGS.LOGSConnection import ResponseTypes

    connection, endpoint, id = dataset._getConnectionData()
    data, responseError = connection.getEndpoint(
                endpoint + [id, "files", "zip"], responseType=ResponseTypes.RAW
            )

    zip_buffer = BytesIO(data)

    file_buffers = {}
    with ZipFile(zip_buffer, 'r') as zip_ref:
        for file_info in zip_ref.filelist:
            file_content = zip_ref.read(file_info.filename)
            file_buffers[file_info.filename] = BytesIO(file_content)
            if verbose:
                print(f"Extracted: {file_info.filename} ({len(file_content)} bytes)")
    return file_buffers
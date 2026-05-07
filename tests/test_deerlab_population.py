import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from deeranalysis.utils import *
from deeranalysis.utils.deerlab_population import *


test_data_folder = r'tests/data/population/'
@pytest.fixture
def datasets():
    twostate_A = eprload(test_data_folder + 'example_twostate_data_1.DSC',test_data_folder + 'example_twostate_data_1.DTA')
    twostate_B = eprload(test_data_folder + 'example_twostate_data_2.DSC',test_data_folder + 'example_twostate_data_2.DTA')
    twostate_A.attrs.update({'title':'twostate_A', 'tau1':400, 'tau2':3600, 'exp_type': '4pDEER'})
    twostate_B.attrs.update({'title':'twostate_B', 'tau1':400, 'tau2':3600, 'exp_type': '4pDEER'})
    twostate_A= twostate_A.assign_coords(t = (twostate_A.coords['X']+ 0.2))
    twostate_B= twostate_A.assign_coords(t = (twostate_B.coords['X']+ 0.2))
    return [twostate_A, twostate_B]


def test_population_data(datasets):
    assert isinstance(datasets, list)
    assert all(isinstance(d, xr.DataArray) for d in datasets)
    assert all('t' in d.coords for d in datasets)
    assert all('title' in d.attrs for d in datasets)
    assert all('tau1' in d.attrs for d in datasets)
    assert all('tau2' in d.attrs for d in datasets)
    assert all('exp_type' in d.attrs for d in datasets)



@pytest.mark.parametrize("pathways", [[1], [2], [1,4]])
def test_population_fitting_function(datasets,pathways):
    result = deerlab_population_fitting(datasets, n_pops=2, pathways=pathways, bg_model=dl.bg_hom3d, r=np.linspace(1.5,6,100))
    assert isinstance(result, dl.FitResult)
    # assert hasattr(result, 'background')




# Testing the model creation functions seperately
@pytest.mark.parametrize("pathways", [[1], [2], [1,4]])
def test_create_Vmodel(datasets, pathways):
    r = np.linspace(1.5,6,100)
    Pmodel = dl.dd_gauss
    Nsignals = len(datasets)
    Vmodels = [[] for _ in range(Nsignals)]
    for n,ds in enumerate(datasets):
        Vmodels[n] = create_Vmodel(ds,ds.coords['t'].values , r, Pmodel,pathways=pathways)

    assert isinstance(Vmodels, list)
    assert all(isinstance(V, dl.Model) for V in Vmodels)
    if len(pathways) == 1:
        assert all(hasattr(V, 'mod') for V in Vmodels)
    else:
        assert all(hasattr(V, f'lam{pathways[0]}') for V in Vmodels)

@pytest.mark.parametrize("pathways", [[1], [2], [1,4]])
def test_model_merging(datasets,pathways):
    r = np.linspace(1.5,6,100); n_pops = 2

    Pmodel = create_multi_pop_model(dl.dd_gauss, n_pops=n_pops)
    Nsignals = len(datasets)
    Vmodels = [[] for _ in range(Nsignals)]
    for n,ds in enumerate(datasets):
        Vmodels[n] = create_Vmodel(ds,ds.coords['t'].values , r, Pmodel,pathways=pathways)
    
    global_model = dl.merge(*Vmodels)

    links_args = {}
    for i in range(n_pops):
        links_args[f"mean{chr(ord('A') + i)}"] = [f"mean{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]
        links_args[f"std{chr(ord('A') + i)}"] = [f"std{chr(ord('A') + i)}_{j+1}" for j in range(Nsignals)]

    global_model = dl.link(global_model, **links_args)

    assert isinstance(global_model, dl.Model)
    assert all(hasattr(global_model, key) for key in links_args.keys())

@pytest.mark.parametrize("pathways", [[1], [2], [1,4]])
def test_build_population_model_data(datasets, pathways):
    model_data = build_population_model_data(
        datasets, n_pops=2, pathways=pathways, bg_model_name='bg_hom3d', 
        dd_model_name='dd_gauss')
    
    assert isinstance(model_data, dict)
    expected_keys = ['meanA','meanB', 'stdA','stdB',]
    if len(pathways) == 1:
        expected_keys += [f'mod_{i+1}' for i in range(len(datasets))]
        expected_keys += [f'reftime_{i+1}' for i in range(len(datasets))]
    else:
        expected_keys += [f'lam{p}_{i+1}' for p in pathways for i in range(len(datasets))]
        expected_keys += [f'reftime{p}_{i+1}' for p in pathways for i in range(len(datasets))]
    assert all(key in model_data['params'] for key in expected_keys)
    assert all(isinstance(model_data['params'][key], dict) for key in expected_keys)


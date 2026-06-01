import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from deeranalysis.utils import *
from deeranalysis.utils.deerlab_global import *

test_data_folder = r'tests/data/benchmark/'

@pytest.fixture
def datasets():
    lab1 = eprload(test_data_folder + 'data_multi_lab1.DSC',test_data_folder + 'data_multi_lab1.DTA')
    lab2 = eprload(test_data_folder + 'data_multi_lab2.DSC',test_data_folder + 'data_multi_lab2.DTA')
    lab1.attrs.update({'file_format': 'BES3T', 'exp_type': '4pDEER'})
    lab1.attrs.update(parse_PulseSpel(lab1.attrs.get('PlsSPELGlbTxt','')))

    lab2.attrs.update({'file_format': 'BES3T', 'exp_type': '4pDEER'})
    lab2.attrs.update(parse_PulseSpel(lab1.attrs.get('PlsSPELGlbTxt','')))


    lab1= lab1.assign_coords(t = (lab1.coords['X']+ lab1.deadtime/1e3))
    lab2= lab2.assign_coords(t = (lab2.coords['X']+ lab2.deadtime/1e3))

    return [lab1, lab2]

def test_population_data(datasets):
    assert isinstance(datasets, list)
    assert all(isinstance(d, xr.DataArray) for d in datasets)
    assert all('t' in d.coords for d in datasets)
    assert all('title' in d.attrs for d in datasets)
    assert all('tau1' in d.attrs for d in datasets)
    assert all('tau2' in d.attrs for d in datasets)
    assert all('exp_type' in d.attrs for d in datasets)


@pytest.mark.parametrize("pathways,linked_params", [
    ([1], ['pr']),
    ([1], ['background']),
    ([1], ['mod-depth']),
    ([1], ['pr', 'background']),
    ([1], ['pr', 'mod-depth']),
    ([1], ['background', 'mod-depth']),
    ([1], ['pr', 'background', 'mod-depth']),
    ([1, 4], ['pr', 'background', 'mod-depth']),
    ([2], ['pr', 'mod-depth']),
])
def test_global_fitting_function(datasets, pathways, linked_params):
    n_datasets = len(datasets)
    result = deerlab_global_fitting(datasets=datasets, pathways=pathways, 
                                    linked_params=linked_params)
    assert isinstance(result, dl.FitResult)
    assert hasattr(result, 'background')
    assert hasattr(result, 'P')
    P = result.P
    assert isinstance(P, list) and len(P) == n_datasets
    assert hasattr(result, 'PUncert')
    PUncert = result.PUncert
    assert isinstance(PUncert, list) and len(PUncert) == n_datasets


def test_global_fitting_export(datasets):
    import io
    result = deerlab_global_fitting(datasets=datasets, pathways=[1], linked_params=['pr'])
    assert isinstance(result, dl.FitResult)
    buf = io.BytesIO()
    dl.save(buf, result, format='hdf5')
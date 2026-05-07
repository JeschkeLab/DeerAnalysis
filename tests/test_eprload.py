import pytest
from deeranalysis.utils.eprload import *
import os
### Bruker BES3T Tests###



def test_eprload_BES3T():
    DSC_file= 'tests/data/benchmark/data_multi_lab1.DSC'
    DTA_file= 'tests/data/benchmark/data_multi_lab1.DTA'
    print(os.getcwd())

    # Load files into bytes
    with open(DSC_file,'rb') as f:
        dsc_content = f.read()
    with open(DTA_file,'rb') as f:
        dta_content = f.read()
    
    dataarray = bes3t_eprload(DSC=dsc_content,DTA=dta_content)
    assert isinstance(dataarray,xr.DataArray)
    assert dataarray.ndim ==1
    assert dataarray.sizes['X'] ==355
    assert 'units' in dataarray.coords['X'].attrs
    assert dataarray.coords['X'].attrs['units'] =='ns'
    assert np.isclose(dataarray.values[0],562303+69661j,rtol=1e-2)
    assert hasattr(dataarray,'datetime') and isinstance(dataarray.datetime, datetime)
    
"""Shared dataset-file parsing logic used by both the single and batch
File Import flows. Kept separate from the Dash callbacks so the same
parsing code can be reused without duplicating it per page.
"""
import base64
import io

import pyepr as pyepr
from deeranalysis.utils.eprload import bes3t_eprload
from deeranalysis.utils.pulsespel_parser import parse_PulseSpel


def get_delays_dict(dataarray):
    """Extracts delay parameters from the dataset attributes."""
    delay_keys = ['tau1', 'tau2', 'tau3', 'tau4', 'tau5', 'tau6']
    return {k: dataarray.attrs[k] for k in delay_keys if k in dataarray.attrs}


def load_bes3t(dsc_content, dta_content):
    """Decodes and loads a Bruker BES3T (.DSC/.DTA) pair into a raw DataArray."""
    dsc_decoded = base64.b64decode(dsc_content.split(',')[1])
    dta_decoded = base64.b64decode(dta_content.split(',')[1])
    return bes3t_eprload(DSC=dsc_decoded, DTA=dta_decoded)


def enrich_bes3t(dataarray):
    """Adds derived attrs/delays to a raw BES3T DataArray and collapses the Y axis if present.

    Returns (dataarray, delays, tmin).
    """
    dataarray.attrs.update({'file_format': 'BES3T'})
    dataarray.attrs.update(parse_PulseSpel(dataarray.attrs.get('PlsSPELGlbTxt', '')))
    delays = get_delays_dict(dataarray)
    tmin = dataarray.attrs.get('deadtime', 0)
    if dataarray.ndim == 2:
        dataarray = dataarray.sum('Y')
    return dataarray, delays, tmin


def load_hdf5(content):
    """Decodes and loads an HDF5 file into a raw DataArray."""
    decoded = base64.b64decode(content.split(',')[1])
    return pyepr.eprload(io.BytesIO(decoded), type='HDF5')


def enrich_hdf5(dataarray, filename):
    """Adds derived title/delays/tmin to a raw HDF5 DataArray. Returns (delays, tmin)."""
    delays = get_delays_dict(dataarray)
    tmin = dataarray.t.values.min() * 1e3
    dataarray.attrs['title'] = filename.split('/')[-1].split('.')[0]
    return delays, tmin


def dataarray_to_store(dataarray, delays, tmin):
    """Converts a parsed DataArray into the dataset-store dict used across the app.

    *tmin* is given in ns (matching the delay parameters/the tmin NumberInput),
    but 't' is in µs, and every consumer of the dataset-store dict (plotting,
    tmin-plausibility checks, saving) adds 'tmin' directly to 't' with no
    further conversion — so it must be stored here in µs already.
    """
    t = dataarray.t.values if 't' in dataarray.coords else dataarray.X.values
    t = t - t[0]
    return {
        'RealData': dataarray.real.values.tolist(),
        'ImagData': dataarray.imag.values.tolist(),
        't': t.tolist(),
        'attrs': dataarray.attrs,
        'delays': delays,
        'tmin': tmin / 1e3,
        'masked_indices': [],
    }


def group_uploaded_files(filenames):
    """Groups a flat list of uploaded filenames into per-dataset groups.

    .DSC/.DTA files sharing a basename are paired together; every other file
    forms its own single-file group. Returns a list of lists of indices into
    *filenames*.
    """
    groups = []
    used = set()
    for i, name in enumerate(filenames):
        if i in used:
            continue
        if name.endswith('.DSC') or name.endswith('.DTA'):
            base = name.rsplit('.', 1)[0]
            pair_ext = '.DTA' if name.endswith('.DSC') else '.DSC'
            partner = next(
                (j for j, other in enumerate(filenames)
                 if j not in used and j != i and other == base + pair_ext),
                None,
            )
            if partner is not None:
                groups.append(sorted([i, partner]))
                used.update([i, partner])
                continue
        groups.append([i])
        used.add(i)
    return groups


def parse_file_group(contents, filenames):
    """Parses one dataset group (1 or 2 files) into a dataset-store dict.

    Returns (store_data, delays_data, title, tmin). Raises ValueError on
    unsupported/invalid input.
    """
    if len(filenames) == 2:
        if {filenames[0].rsplit('.', 1)[-1], filenames[1].rsplit('.', 1)[-1]} != {'DSC', 'DTA'}:
            raise ValueError("Expected a matching .DSC and .DTA file pair.")
        if filenames[0].endswith('.DSC'):
            dsc_content, dta_content = contents[0], contents[1]
        else:
            dsc_content, dta_content = contents[1], contents[0]
        dataarray = load_bes3t(dsc_content, dta_content)
        dataarray, delays, tmin = enrich_bes3t(dataarray)
    elif filenames[0].endswith('.h5'):
        dataarray = load_hdf5(contents[0])
        delays, tmin = enrich_hdf5(dataarray, filenames[0])
    elif filenames[0].endswith('.DSC') or filenames[0].endswith('.DTA'):
        raise ValueError("Missing matching .DSC/.DTA file — upload both files together.")
    else:
        raise ValueError("Unsupported file type. Only .DSC/.DTA (Bruker BES3T) and .h5 (HDF5) are supported here.")

    store_data = dataarray_to_store(dataarray, delays, tmin)
    delays_data = [{'parameter': k, 'value': v} for k, v in delays.items()]
    title = dataarray.attrs.get('title', filenames[0].rsplit('.', 1)[0].split('/')[-1])
    return store_data, delays_data, title, tmin

import os
from datetime import datetime

import numpy as np
from numpy import savetxt, column_stack

from deeranalysis.utils import dataarray_from_database_entry
import deerlab as dl

def save_bruker_bes3t(filename, x, data, title='', mw_freq=np.nan):
    """Save data in Bruker BES3T format (.DTA + .DSC files).

    Parameters
    ----------
    filename : str
        Output filename, with or without .DTA/.DSC extension.
    x : array-like or list of two array-likes
        X-axis values for 1D data, or ``[x_axis, y_axis]`` for 2D data.
    data : array-like
        Signal data (real or complex). For 2D data, shape must be
        ``(len(x_axis), len(y_axis))``.
    title : str, optional
        Dataset title shown in Bruker software.
    mw_freq : float, optional
        Microwave frequency in GHz.
    """
    # Strip known extensions
    base, ext = os.path.splitext(filename)
    if ext.upper() in ('.DTA', '.DSC', '.XGF', '.YGF'):
        filename = base

    data = np.asarray(data)
    if data.ndim > 2:
        raise ValueError("Cannot save data with more than 2 dimensions.")

    two_dim = data.ndim == 2 and min(data.shape) > 1

    if two_dim:
        if not (isinstance(x, (list, tuple)) and len(x) == 2):
            raise ValueError("For 2D data, x must be a list/tuple of two axes.")
        x_axis = np.asarray(x[0], dtype=np.float64).ravel()
        y_axis = np.asarray(x[1], dtype=np.float64).ravel()
    else:
        if isinstance(x, (list, tuple)):
            x_axis = np.asarray(x[0], dtype=np.float64).ravel()
        else:
            x_axis = np.asarray(x, dtype=np.float64).ravel()
        y_axis = None

    complex_data = not np.isrealobj(data)
    byteorder = 'big'  # BES3T default (XEPR/Linux)
    bes3t_version = '1.2'

    # --- Write .DTA binary file ---
    dta_path = filename + '.DTA'
    # Flatten column-major (Fortran order) to match MATLAB data(:)
    flat = data.flatten('F')
    if complex_data:
        interleaved = np.empty(2 * len(flat), dtype=np.float64)
        interleaved[0::2] = flat.real
        interleaved[1::2] = flat.imag
        raw = interleaved
    else:
        raw = flat.real.astype(np.float64)

    with open(dta_path, 'wb') as f:
        f.write(raw.astype('>f8').tobytes())

    # --- Write .DSC descriptor file ---
    dsc_path = filename + '.DSC'
    now = datetime.now()

    def _is_linear(axis):
        diffs = np.diff(axis)
        if len(diffs) == 0:
            return True
        mn, mx = diffs.min(), diffs.max()
        if mn == 0:
            return False
        return abs(mx / mn - 1) < 1e-5

    x_linear = _is_linear(x_axis)
    x_type = 'IDX' if x_linear else 'IGD'
    if two_dim:
        y_linear = _is_linear(y_axis)
        y_type = 'IDX' if y_linear else 'IGD'
    else:
        y_type = 'NODATA'

    with open(dsc_path, 'w') as f:
        def kv(key, val):
            f.write(f'{key}\t{val}\n')

        def line(val=''):
            f.write(f'{val}\n')

        f.write(f'* Exported from DeerAnalysis, {now.strftime("%Y-%m-%d %H:%M:%S")}\n')
        kv('#DESC', f'{bes3t_version} * DESCRIPTOR INFORMATION ***********************')
        kv('DSRC', 'MAN')
        kv('BSEQ', 'BIG' if byteorder == 'big' else 'LIT')
        kv('IKKF', 'CPLX' if complex_data else 'REAL')
        kv('IRFMT', 'D')
        if complex_data:
            kv('IIFMT', 'D')

        # Write XGF gauge file if X axis is non-linear
        if not x_linear:
            xgf_path = filename + '.XGF'
            with open(xgf_path, 'wb') as gf:
                gf.write(x_axis.astype('>f8').tobytes())
            kv('XFMT', 'D')

        # Write YGF gauge file if Y axis is non-linear
        if two_dim and not y_linear:
            ygf_path = filename + '.YGF'
            with open(ygf_path, 'wb') as gf:
                gf.write(y_axis.astype('>f8').tobytes())
            kv('YFMT', 'D')

        kv('XTYP', x_type)
        kv('YTYP', y_type)
        kv('ZTYP', 'NODATA')

        kv('XPTS', str(len(x_axis)))
        kv('XMIN', f'{x_axis[0]:g}')
        kv('XWID', f'{x_axis[-1] - x_axis[0]:g}')
        if two_dim:
            kv('YPTS', str(len(y_axis)))
            kv('YMIN', f'{y_axis[0]:g}')
            kv('YWID', f'{y_axis[-1] - y_axis[0]:g}')

        if title:
            kv('TITL', f"'{title}'")

        line('*')
        line('************************************************************')
        line('*')
        kv('#SPL', f'{bes3t_version} * STANDARD PARAMETER LAYER')
        kv('OPER', '')
        kv('DATE', now.strftime('%d/%m/%y'))
        kv('TIME', now.strftime('%H:%M:%S'))
        kv('CMNT', '')
        kv('SAMP', '')
        kv('SFOR', '')
        if not (isinstance(mw_freq, float) and np.isnan(mw_freq)):
            kv('MWFQ', f'{mw_freq * 1e9:.9g}')


def datasetSQL_to_file(file, dataset_entry, format_type):
    """
    Saves a dataset from the database to a file in the specified format. Supported formats include:
    - CSV: A simple text format with comma-separated values. The output will have three columns: time (t), real part of the signal (V_real), and imaginary part of the signal (V_imag).
    - MAT: MATLAB format, which can be easily loaded in Python using scipy.io.loadmat or in MATLAB itself. The output will contain the time (t), complex signal (V), and metadata fields such as name, project, sample, and exp.
    - HDF5: A hierarchical data format that can store large amounts of data efficiently. The output will contain datasets for time (t), complex signal (V), and metadata fields as attributes of the HDF5 file.
    - Bruker: A proprietary format used by Bruker

    Parameters:
    -----------
    file: 
        A file-like object or file path where the dataset will be saved.
    dataset:
        A Dataset database entry object containing the data and metadata to be saved.
    format_type: str
        The format in which to save the dataset. Supported values are 'csv', 'mat',

    
    """

    if format_type == 'csv':

        t = np.array(dataset_entry.t)
        V = np.array(dataset_entry.V) + 1j*np.array(dataset_entry.V_im)
        data = column_stack((t, V.real, V.imag))
        header = 't,V_real,V_imag'
        savetxt(file, data, delimiter=',', header=header, comments='')
    
    elif format_type == 'matlab':

        from scipy.io import savemat
        t = np.array(dataset_entry.t)
        V = np.array(dataset_entry.V) + 1j*np.array(dataset_entry.V_im)
        output_dict = {}
        output_dict['t'] = t.T
        output_dict['V'] = V.T
        output_dict['name'] = dataset_entry.name
        output_dict['project'] = dataset_entry.project
        output_dict['sample'] = dataset_entry.sample
        output_dict['exp'] = dataset_entry.exp


        savemat(file, output_dict)
    
    elif format_type == 'h5':
        dataset = dataarray_from_database_entry(dataset_entry)

        dataset.epr.save(file)
    
    elif format_type == 'Bruker':
        t = np.array(dataset_entry.t)
        V = np.array(dataset_entry.V) + 1j * np.array(dataset_entry.V_im)
        title = getattr(dataset_entry, 'name', '') or ''
        mw_freq = getattr(dataset_entry, 'mwFreq', np.nan)
        if mw_freq is None:
            mw_freq = np.nan
        save_bruker_bes3t(file, t, V, title=title, mw_freq=mw_freq)
    
    else:
        raise ValueError(f"Unsupported format type: {format_type}") 

def output_to_file(file, output, format_type):

    if format_type == 'csv':
        # Create a zip file with two CSVs: one for the time domain data and one for the distance distribution
        from zipfile import ZipFile
        import io
        time_buffer = io.StringIO()
        dist_buffer = None # Only create if needed later

        # Save time domain data
        header = 't'
        data_list = [output['t']]
        if np.iscomplexobj(output['Vexp']):
            header += ',V_exp_real,V_exp_imag'
            data_list.append(output['Vexp'].real)
            data_list.append(output['Vexp'].imag)
        else:
            header += ',V_exp'
            data_list.append(output['Vexp'])
        if 'Vmodel' in output and output['Vmodel'] is not None:
            if np.iscomplexobj(output['Vmodel']):
                header += ',V_model_real,V_model_imag'
                data_list.append(output['Vmodel'].real)
                data_list.append(output['Vmodel'].imag)
            else:
                header += ',V_model'
                data_list.append(output['Vmodel'])
        if 'bg' in output and output['bg'] is not None:
            if np.iscomplexobj(output['bg']):
                header += ',bg_real,bg_imag'
                data_list.append(output['bg'].real)
                data_list.append(output['bg'].imag)
            else:
                header += ',bg'
                data_list.append(output['bg'])
        data = column_stack(data_list)
        savetxt(time_buffer, data, delimiter=',', header=header, comments='')

        # Save distance distribution data
        if 'r' in output:
            dist_buffer = io.StringIO()
            header = 'r,P'
            data_list = [output['r'], output['P']]
            if 'P_lb' in output and 'P_ub' in output and output['P_lb'] is not None and output['P_ub'] is not None:
                header += ',lb,ub'
                data_list.append(output['P_lb'])
                data_list.append(output['P_ub'])
            data = column_stack(data_list)

            savetxt(dist_buffer, data, delimiter=',', header=header, comments='')
        
        if isinstance(file, str):
            with ZipFile(file, 'w') as zip_file:
                zip_file.writestr(f'{file}_t.csv', time_buffer.getvalue())
                if dist_buffer is not None:
                    zip_file.writestr(f'{file}_dd.csv', dist_buffer.getvalue())
        else:
            with ZipFile(file, 'w') as zip_file:
                zip_file.writestr('fit_t.csv', time_buffer.getvalue())
                if dist_buffer is not None:
                    zip_file.writestr('fit_dd.csv', dist_buffer.getvalue())


    elif format_type == 'matlab':
        from scipy.io import savemat
        savemat(file, output)

    else:
        raise ValueError(f"Unsupported format type: {format_type}")


def FitResult_to_file(file, fitresult, format_type, uncert=True):

    output = {}
    output['t'] = fitresult.t
    output['Vexp'] = fitresult.Vexp
    output['Vmodel'] = fitresult.model if fitresult.model is not None else None

    if hasattr(fitresult, 'bg'):
        output['bg'] = fitresult.bg
    
    if hasattr(fitresult, 'r') and hasattr(fitresult, 'P'):
        output['r'] = fitresult.r
        output['P'] = fitresult.P
        if uncert:
            output['P_lb'] = fitresult.PUncert.ci(95)[:,0]
            output['P_ub'] = fitresult.PUncert.ci(95)[:,1]

    output_to_file(file, output, format_type)


def _convert_lists_in_dicts_to_arrays(d):
    """Recursively convert lists in a dict to numpy arrays."""
    if isinstance(d, dict):
        return {k: _convert_lists_in_dicts_to_arrays(v) for k, v in d.items()}
    elif isinstance(d, list):
        return np.array(d)
    else:
        return d


def fitSQL_to_file(file, fit_entry,dataset_entry, format_type, uncert=True):
    output = {}
    output['t'] = np.array(dataset_entry.t)
    output['Vexp'] = np.array(dataset_entry.V) + 1j*np.array(dataset_entry.V_im)

    output['Vmodel'] = np.array(fit_entry.model)
    output['r'] = np.array(fit_entry.r)
    output['P'] = np.array(fit_entry.P_model)
    if isinstance(fit_entry.PUncert, dict): #
        PUncert = PUncert = dl.UQResult.from_dict(_convert_lists_in_dicts_to_arrays(fit_entry.PUncert))
        output['P_lb'] = np.array(PUncert.ci(95)[:,0])
        output['P_ub'] = np.array(PUncert.ci(95)[:,1])

    output['bg'] = np.array(fit_entry.background) if fit_entry.background is not None else None
    if fit_entry.engine == 'DeerNet':
        # Either resample the fit to the dataset's t axis or 
        Vt = np.array(fit_entry.t)
        output['Vmodel'] = np.interp(output['t'], Vt, output['Vmodel'])
        if output['bg'] is not None:
            output['bg'] = np.interp(output['t'], Vt, output['bg'])
    
    output_to_file(file, output, format_type)


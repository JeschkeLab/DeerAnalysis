import numpy as np
from numpy import savetxt, column_stack

from deeranalysis.utils import dataarray_from_database_entry


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
    
    elif format_type =='Bruker':
        raise NotImplementedError("Bruker format export is not implemented yet.")
    
    else:
        raise ValueError(f"Unsupported format type: {format_type}") 



def fitSQL_to_file(file, fit_entry,dataset_entry, format_type, uncert=True):

    t = np.array(dataset_entry.t)
    Vexp = np.array(dataset_entry.V) + 1j*np.array(dataset_entry.V_im)

    Vmodel = np.array(fit_entry.model)
    r = np.array(fit_entry.r)
    P = np.array(fit_entry.P_model)
    P_lb = np.array(fit_entry.P_model['lb']) if fit_entry.P_model and 'lb' in fit_entry.P_model else None
    P_ub = np.array(fit_entry.P_model['ub']) if fit_entry.P_model and 'ub' in fit_entry.P_model else None

    if fit_entry.engine == 'DeerNet':
        # Either resample the fit to the dataset's t axis or 
        Vt = np.array(fit_entry.t)
        Vmodel = np.interp(t, Vt, Vmodel)
        raise NotImplementedError("Resampling of DeerNet fits is not implemented yet. Please ensure that the fit and dataset have the same time axis before exporting.")
        
    if format_type == 'csv':
        # Create a zip file with two CSVs: one for the time domain data and one for the distance distribution
        from zipfile import ZipFile
        import io
        time_buffer = io.StringIO()
        dist_buffer = io.StringIO()

        # Save time domain data
        header = 't,V_exp_real,V_exp_imag,V_model'
        data = column_stack((t, Vexp.real, Vexp.imag, Vmodel.real))
        savetxt(time_buffer, data, delimiter=',', header=header, comments='')

        # Save distance distribution data
        header = 'r,P'
        if uncert and P_lb is not None and P_ub is not None:
            header = 'r,P,lb,ub'
            data = column_stack((r, P, P_lb, P_ub))
        else:
            header = 'r,P'
            data = column_stack((r, P))
        savetxt(dist_buffer, data, delimiter=',', header=header, comments='')
        
        if isinstance(file, str):
            with ZipFile(file, 'w') as zip_file:
                zip_file.writestr(f'{file}_t.csv', time_buffer.getvalue())
                zip_file.writestr(f'{file}_dd.csv', dist_buffer.getvalue())
        else:
            with ZipFile(file, 'w') as zip_file:
                zip_file.writestr('fit_t.csv', time_buffer.getvalue())
                zip_file.writestr('fit_dd.csv', dist_buffer.getvalue())


    elif format_type == 'matlab':
        from scipy.io import savemat
        output_dict = {}
        output_dict['t'] = t.T
        output_dict['V_exp'] = Vexp.T
        output_dict['V_model'] = Vmodel.T
        output_dict['r'] = r.T
        output_dict['P'] = P.T
        if uncert and P_lb is not None and P_ub is not None:
            output_dict['P_uncert'] = np.array([P_lb, P_ub]).T
            
        savemat(file, output_dict)

    else:
        raise ValueError(f"Unsupported format type: {format_type}")
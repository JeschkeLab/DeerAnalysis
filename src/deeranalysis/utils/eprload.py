import numpy as np
import xarray as xr
from warnings import warn
import re
import os
from datetime import datetime

def eprload(*filenames, file_format=None, **kwargs):
    """
    Loads EPR data from various file formats from filenames.

    Supported formats:
    - Bruker BES3T (.DSC and .DTA files, plus optional .XGF, .YGF, .ZGF companion files)

    Parameters
    ----------
    filenames : str or list
        One or more filenames (for BES3T only) to load. Only one dataset at a time is supported.
    file_format : str, optional
        The format of the files. If None, the format is inferred from the file extension.
    **kwargs : dict
        Additional keyword arguments passed to xarray.DataArray constructor.
    """
    
    if not isinstance(filenames, (list, tuple)):
        filenames = [filenames]
        
    if isinstance(filenames[0],dict):
        # If a dict of filename: filebuffer is provided, extract the buffers and filenames
        filebuffers = list(filenames[0].values())
        filenames = list(filenames[0].keys())
    else:
        filebuffers = None
    
    

    # check if 'DSC' or 'DTA' in file endings
    if file_format is None:
        file_endings = [os.path.splitext(fname)[1].upper() for fname in filenames]
        if '.DSC' in file_endings or '.DTA' in file_endings:
            file_format = 'BES3T'
        else:
            raise ValueError("Could not infer file format from extensions. Please specify 'file_format' parameter.")
    
    if file_format == 'BES3T':
        # Ensure both .DSC and .DTA files are provided
        if len(filenames) < 2:
            raise ValueError("Please provide both .DSC and .DTA files for Bruker BES3T format.")
        
        dsc_file = None
        dta_file = None
        xgf_file = None
        ygf_file = None
        zgf_file = None
        
        if filebuffers is None:
            for fname in filenames:
                ext = os.path.splitext(fname)[1].upper()
                with open(fname, 'rb') as f:
                    if ext == '.DSC':
                        dsc_file = f.read()
                    elif ext == '.DTA':
                        dta_file = f.read()
                    elif ext == '.XGF':
                        xgf_file = f.read()
                    elif ext == '.YGF':
                        ygf_file = f.read()
                    elif ext == '.ZGF':
                        zgf_file = f.read()
        else:
            for fname, fbuffer in zip(filenames, filebuffers):
                ext = os.path.splitext(fname)[1].upper()
                if ext == '.DSC':
                    dsc_file = fbuffer.read()
                elif ext == '.DTA':
                    dta_file = fbuffer.read()
                elif ext == '.XGF':
                    xgf_file = fbuffer.read()
                elif ext == '.YGF':
                    ygf_file = fbuffer.read()
                elif ext == '.ZGF':
                    zgf_file = fbuffer.read()
        
        if dsc_file is None or dta_file is None:
            raise ValueError("Both .DSC and .DTA files must be provided for Bruker BES3T format.")
        
        dataarray = bes3t_eprload(dsc_file, dta_file, XGF=xgf_file, YGF=ygf_file, ZGF=zgf_file, **kwargs)
        return dataarray
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


### Bruker BES3T EPR data loading function
def bes3t_eprload(DSC, DTA,XGF=None,YGF=None,ZGF=None, **kwargs):
    """Loads and parses Bruker BES3T EPR data files (.DSC and .DTA).
    If a companion file (.XGF, .YGF, .ZGF) is present it must also be supplied as a keyword argument.
    Parameters
    ----------
    DSC_file : bytes
        Content of the .DSC file as bytes.
    DTA : bytes
        Content of the .DTA file as bytes.
    XGF : bytes, optional
        Content of the .XGF companion file as bytes, by default None.
    YGF : bytes, optional
        Content of the .YGF companion file as bytes, by default None.
    ZGF : bytes, optional
        Content of the .ZGF companion file as bytes, by default None.
    **kwargs : dict
        Additional keyword arguments passed to xarray.DataArray constructor.

    returns
    -------
    dataarray : xarray.DataArray
        The loaded EPR data as an xarray DataArray.
    
    
    Notes
    -----
    Code based on BES3T version 1.2 (Xepr >=2.1), and DeerLab `deerload` function.

    """

    # Read the description file
    parameters = _read_des3t_dsc_file(DSC)
    parDESC = parameters['DESC']
    parSPL = parameters.get('SPL', {})



    # XPTS, YPTS, ZPTS specify the number of data points along x, y and z.
    if 'XPTS' in parDESC:
        nx = int(parDESC['XPTS'])
    else:
        raise ValueError('No XPTS in DSC file.')
    
    if 'YPTS' in parDESC:
        ny = int(parDESC['YPTS'])
    else:
        ny = 1
    if 'ZPTS' in parDESC:
        nz = int(parDESC['ZPTS'])
    else:
        nz = 1
        # BSEQ: Byte Sequence
    # BSEQ describes the byte order of the data, big-endian (BIG, encoding = '>') or little-endian (LIT, encoding = '<').
    if 'BSEQ' in parDESC:
        if 'BIG' == parDESC['BSEQ']:
            byteorder = '>' 
        elif 'LIT' == parDESC['BSEQ']:
            byteorder = '<'
        else:
            raise ValueError('Unknown value for keyword BSEQ in .DSC file!')
    else:
        warn('Keyword BSEQ not found in .DSC file! Assuming BSEQ=BIG.')
        byteorder = '>'
    
    # IRFMT: Item Real Format
    # IIFMT: Item Imaginary Format
    # Data format tag of BES3T is IRFMT for the real part and IIFMT for the imaginary part.
    if 'IRFMT' in parDESC:
        IRFTM = parDESC["IRFMT"]
        if 'C' == IRFTM:
            dt_spc = np.dtype('int8')
        elif 'S' == IRFTM:
            dt_spc = np.dtype('int16')
        elif 'I' == IRFTM:
            dt_spc = np.dtype('int32')
        elif 'F' == IRFTM:
            dt_spc = np.dtype('float32')
        elif 'D' == IRFTM:
            dt_spc = np.dtype('float64')
        elif 'A' == IRFTM:
            raise TypeError('Cannot read BES3T data in ASCII format!')
        elif ('0' or 'N') == IRFTM:
            raise ValueError('No BES3T data!')
        else:
            raise ValueError('Unknown value for keyword IRFMT in .DSC file!')
    else:
        raise ValueError('Keyword IRFMT not found in .DSC file!')
    
    # IRFMT and IIFMT must be identical.
    if "IIFMT" in parDESC:
        if  parDESC["IIFMT"] != parDESC["IRFMT"]:
            raise ValueError("IRFMT and IIFMT in DSC file must be identical.")
    
    # Preallocation of the abscissa
    maxlen = max(nx,ny,nz)
    abscissa = np.full((maxlen,3),np.nan)
    # Construct abscissa vectors
    AxisNames = ['X','Y','Z']
    Dimensions = [nx,ny,nz]
    AxisUnits = ['','','']
    for a in AxisNames:
        index = AxisNames.index(a)
        axisname = a+'TYP'
        axistype = parDESC[axisname]
        AxisUnits[index] = parDESC.get(a+'UNI','')
        if Dimensions[index] == 1:
            pass
        else:
            if 'IGD'== axistype:
                # Nonlinear axis -> Try to read companion file (.XGF, .YGF, .ZGF)
                # companionfilename=str(filename+'.'+a+'GF')
                if 'D' == parDESC[str(a+'FMT')]:
                    dt_axis = np.dtype('float64')
                elif 'F' == parDESC[str(a+'FMT')]:
                    dt_axis = np.dtype('float32')
                elif 'I' == parDESC[str(a+'FMT')]:
                    dt_axis = np.dtype('int32')
                elif 'S' == parDESC[str(a+'FMT')]:
                    dt_axis = np.dtype('int16')
                else:
                    raise ValueError(f'Cannot read data format {a+"FMT"} for companion file')

                dt_axis = dt_axis.newbyteorder(byteorder)
                # Open and read companion file
                fileBytes = locals()[f'{a}GF']
                try:
                    abscissa[:Dimensions[index],index] = np.frombuffer(fileBytes,dtype=dt_axis)
                except:
                    warn(f"Could not read companion file f'{a}GF' for nonlinear axis. Assuming linear axis.")
                    axistype='IDX'
        if axistype == 'IDX':
            minimum = float(parDESC[str(a+'MIN')])
            width = float(parDESC[str(a+'WID')])
            npts = int(parDESC[str(a+'PTS')])
            if width == 0:
                warn(f'Warning: {a} range has zero width.\n')
                minimum = 1.0
                width = len(a) - 1.0
            abscissa[:Dimensions[index],index] = np.linspace(minimum,minimum+width,npts)
        if axistype == 'NTUP':
            raise ValueError('Cannot read data with NTUP axes.')

    dt_data = dt_spc
    dt_spc = dt_spc.newbyteorder(byteorder)
    # Read data matrix and separate complex case from real case.
    data = np.full((nx,ny,nz),np.nan)
    # reorganize the data in a "complex" way as the real part and the imaginary part are separated
    # IKKF: Complex-data Flag
    # CPLX indicates complex data, REAL indicates real data.
    if 'IKKF' in parDESC:
        if parDESC['IKKF'] == 'REAL':
            data = np.full((nx,ny,nz),np.nan) 
            data = np.frombuffer(DTA,dtype=dt_spc)
            # with open(filename_dta,'rb') as fp:
            #      data = np.frombuffer(fp.read(),dtype=dt_spc)
            data = np.copy(data)
        elif parDESC['IKKF'] == 'CPLX':
            dt_new = np.dtype('complex')
            data = np.frombuffer(DTA,dtype=dt_spc)

            # with open(filename_dta,'rb') as fp:
            #     data = np.frombuffer(fp.read(),dtype=dt_spc)
                # Check if there is multiple harmonics (High field ESR quadrature detection)
            harmonics = np.array([[False] * 5]*2) # outer dimension for the 90 degree phase
            for j,jval in enumerate(['1st','2nd','3rd','4th','5th']):
                for k,kval in enumerate(['','90']):
                    thiskey = 'Enable'+jval+'Harm'+kval
                    if thiskey in parameters.keys() and parameters[thiskey]:
                        harmonics[k,j] = True
            n_harmonics = sum(harmonics)[0]
            if n_harmonics != 0:
                ny = int(len(data)/nx/n_harmonics)

            # copy the data to a writable numpy array
            data = np.copy(data.astype(dtype=dt_data).view(dtype=dt_new))
        else:
            raise ValueError("Unknown value for keyword IKKF in .DSC file!")
    else:
        warn("Keyword IKKF not found in .DSC file! Assuming IKKF=REAL.")
    
    # Split 1D-array into 3D-array according to XPTS/YPTS/ZPTS 
    data = np.array_split(data,nz)
    data = np.array(data).T
    data = np.array_split(data,ny)
    data = np.array(data).T

    # Ensue proper numpy formatting
    data = np.atleast_1d(data)
    data = np.squeeze(data)

    # Abscissa formatting
    abscissa = np.atleast_1d(abscissa)
    abscissa = np.squeeze(abscissa)
    abscissas = []
    # Convert to list of abscissas 
    for absc in abscissa.T:
        # Do not include abcissas full of NaNs
        if not all(np.isnan(absc)):
            # ns -> µs converesion
            absc /= 1e3
            # Remove nan values to ensure proper length of abscissa
            abscissas.append(absc[~np.isnan(absc)])
    # # If 1D-dataset, return array instead of single-element list
    # if len(abscissas)==1:
    #     abscissas = abscissas[0]

    # build coordinates and dims for xarray DataArray
    coords =kwargs.get('coords', {}) # Get any existing coords from kwargs
    for i in range(data.ndim):
        coord_name = AxisNames[i]
        if Dimensions[i] == 1:
            # squeeze dimension
            data = np.squeeze(data, axis=i)
        else:
            coords[coord_name] = (coord_name, abscissas[i], {'units': AxisUnits[i]})

    attrs = kwargs.get('attrs', {}) # Get any existing attrs from kwargs
    attrs['title'] = parDESC.get('TITL','')
    attrs['datetime'] = extract_datetime(parSPL)
    attrs.update(extract_key_parameters(parameters))
    attrs.update(extract_PulseSpel_files(parameters))

    return xr.DataArray(data, coords=coords, dims=['X','Y','Z'][:data.ndim], **kwargs,attrs=attrs)

def _read_des3t_dsc_file(DSC_file):
    """
    Reads and parses a Bruker BES3T .DSC file.
    Parameters
    ----------
    DSCFileName : bytes
        Content of the .DSC file as bytes.
    """
    # check encoding is utf-8
    if isinstance(DSC_file, bytes):
        try:
            DSC_file = DSC_file.decode('utf-8', errors='ignore')
        except (UnicodeDecodeError, AttributeError):
            raise ValueError("The .DSC file is not encoded in UTF-8 format.")
    elif not isinstance(DSC_file, str):
        raise TypeError("DSC_file must be bytes or str")

    allLines = DSC_file.splitlines(keepends=False)
    
    # Remove lines with comments
    allLines = [l for l in allLines if not l.startswith("*")]

    # Remove newlines (handle Unix and Windows line endings)
    allLines = [l.rstrip("\r\n") for l in allLines]
    
    # Remove empty lines
    allLines = [l for l in allLines if l]
    
    # Merge any line ending in \n\ with the subsequent one
    allLines2 = []
    val = ""
    for line in allLines:
        val = "".join([val, line])    
        if val.endswith("\\"):
            val = val.strip("\\")
        else:
            allLines2.append(val)
            val = ""
    allLines = allLines2
    
    Parameters = {}
    SectionName = None
    DeviceName = None
    
    # Regular expressions to match layer/section headers, device block headers, and key-value lines
    reSectionHeader = re.compile(r"#(\w+)\W+(\d+.\d+)")
    reDeviceHeader = re.compile(r"\.DVC\W+(\w+),\W+(\d+\.\d+)")
    reKeyValue = re.compile(r"(\w+)\W+(.*?)'?$")
    
    for nline,line in enumerate(allLines):

        if 'MANIPULATION HISTORY LAYER' in line:
            break
        # Layer/section header (possible values: #DESC, #SPL, #DSL, #MHL)
        mo1 = reSectionHeader.search(line) 
        if mo1:
            SectionName = mo1.group(1)
            SectionVersion = mo1.group(2)
            if SectionName not in {"DESC","SPL","DSL","MHL"}:
                raise ValueError("Found unrecognized section " + SectionName + ".")
            Parameters[SectionName] = {"_version": SectionVersion}
            DeviceName = None
            continue
        
        # Device block header (starts with .DVC)
        mo2 = reDeviceHeader.search(line)
        if mo2:
            DeviceName = mo2.group(1)
            DeviceVersion = mo2.group(2)
            Parameters[SectionName][DeviceName] = {"_version": DeviceVersion}
            continue
        
        # Key/value entry
        mo3 = reKeyValue.search(line)
        if not mo3:
            warn(f"Key/value pair expected on line {nline}.")
            continue 
               
        if not SectionName:
            raise ValueError("Found a line with key/value pair outside any layer.")
        if SectionName=="DSL" and not DeviceName:
            raise ValueError("Found a line with key-value pair outside .DVC in #DSL layer.")
        
        Key = mo3.group(1)
        Value = mo3.group(2)
        if DeviceName:
            Parameters[SectionName][DeviceName][Key] = Value
        else:
            Parameters[SectionName][Key] = Value
    
        # Assert DESC section is present
        if "DESC" not in Parameters:
            raise ValueError("Missing DESC section in .DSC file.")
    
    return Parameters

def extract_key_parameters(parameters):

    """ Extracts key parameters from the DESC section of a BES3T .DSC file.

    Parameters
    ----------
    parameters : dict
        A dict of dicts of parameters as returned by _read_des3t_dsc_file.

    Returns
    -------
    params : dict
        A dictionary containing extracted key parameters.
    """
    #Flatten parameters so all keys are accessible at the top level
    new_parameters = {}
    for section, content in parameters.items():
        if section == 'DSL':
            for device, dev_content in content.items():
                if device == '_version':
                    continue
                new_parameters.update(dev_content)
        else:
            new_parameters.update(content)
    parameters = new_parameters

    params = {}
    
    if 'CenterField' in parameters:
        params['B'] = _string_to_G(parameters['CenterField'])
    if 'FrequencyMon' in parameters:
        params['freq'] = _string_to_GHz(parameters['FrequencyMon'])
    if 'ShotRepTime' in parameters:
        params['reptime'] = _string_to_us(parameters['ShotRepTime'])
    if 'ShotsPLoop' in parameters:
        params['nshots'] = int(parameters['ShotsPLoop'])
    if 'NbScansAcc' in parameters:
        params['nscans'] = int(parameters['NbScansAcc'])


    return params
    
def extract_PulseSpel_files(parameters):
    """
    Extracts the pulse spel file, both the .exp and .def parts, from the parameters dictionary.
    """

    params = {}
    try:
        params['PlsSPELPrgTxt'] = parameters['DSL']['ftEpr']['PlsSPELPrgTxt']
        params['PlsSPELPrgTxt'] = params['PlsSPELPrgTxt'].replace('\\n', '\n')
        params['PlsSPELGlbTxt'] = parameters['DSL']['ftEpr']['PlsSPELGlbTxt']
        params['PlsSPELGlbTxt'] = params['PlsSPELGlbTxt'].replace('\\n', '\n')
    except KeyError:
        warn(r"Pulsespel files not found in DSC parameters.")
    except Exception as e:
        warn(f"Error extracting Pulsespel files: {str(e)}")

    return params


def _string_to_G(str):
    # Split the string into number and unit, if unit is missing, assume G
    match = re.match(r"([\d.]+)\s*([a-zA-Z]*)", str.strip())
    if match:
        number = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'G':
            return number
        elif unit == 'T':
            return number * 1e4
        elif unit == 'mT':
            return number * 10
        elif unit == '':
            return number
        else:
            raise ValueError(f"Unknown magnetic field unit: {unit}")
    else:
        raise ValueError(f"Invalid magnetic field string: {str}")

def _string_to_GHz(str):
    # Split the string into number and unit, if unit is missing, assume GHz
    match = re.match(r"([\d.]+)\s*([a-zA-Z]*)", str.strip())
    if match:
        number = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'GHZ':
            return number
        elif unit == 'MHZ':
            return number / 1e3
        elif unit == 'KHZ':
            return number / 1e6
        elif unit == '':
            return number
        else:
            raise ValueError(f"Unknown frequency unit: {unit}")
        
def _string_to_ns(str):
    # Split the string into number and unit, if unit is missing, assume ns
    match = re.match(r"([\d.]+)\s*([a-zA-Z]*)", str.strip())
    if match:
        number = float(match.group(1))
        unit = match.group(2).lower()
        if unit == 'ns':
            return number
        elif unit == 'us':
            return number * 1e3
        elif unit == 'ms':
            return number * 1e6
        elif unit == '':
            return number
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    else:
        raise ValueError(f"Invalid time string: {str}")

def _string_to_us(str):
    # Split the string into number and unit, if unit is missing, assume us
    match = re.match(r"([\d.]+)\s*([a-zA-Z]*)", str.strip())
    if match:
        number = float(match.group(1))
        unit = match.group(2).lower()
        if unit == 'us':
            return number
        elif unit == 'ns':
            return number / 1e3
        elif unit == 'ms':
            return number * 1e3
        elif unit == '':
            return number
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    else:
        raise ValueError(f"Invalid time string: {str}")



def dataarray_from_database_entry(db_entry):

    t= np.array(db_entry.t)
    V = np.array(db_entry.V) + 1j * np.array(db_entry.V_im)
    attrs = {
        'name': db_entry.name,
        'project': db_entry.project,
        'sample': db_entry.sample,
        'seq_name': db_entry.exp,}
    attrs.update(db_entry.meta)
    attrs.update(db_entry.delays)
    

    return xr.DataArray(V, coords={'t': ('t', t, {'units':'µs'})}, dims=['t'], attrs=attrs)


def search_variable(var_dict, search_terms, variable_type,one_item=False):
    """
    
    Search for variables in var_dict based on search_terms and variable_type.

    Parameters:
    -----------
    var_dict : dict
        Dictionary containing variable information.
    search_terms : str or list
        Terms to search for in the variable comments.
    variable_type : str
        Type of variable to filter ('delay', 'pulse', 'counter') or None.
    one_item : bool
        If True, only return one matching item.
    """
    # search_terms = 'tau1'
# variable_type='delay'
    if isinstance(search_terms, str):
        search_terms = [search_terms]
    found_items = {key: val for key, val in var_dict.items() if any(term in val[1] for term in search_terms)}
    if variable_type=='delay':
        # Only keep keys that start with 'd'
        found_items = {key: val for key, val in found_items.items() if key.startswith('d')}
    elif variable_type=='pulse':
        # Only keep keys that start with 'p'
        found_items = {key: val for key, val in found_items.items() if key.startswith('p')}
    elif variable_type=='counter':
        # Only keep keys that contain no numbers
        found_items = {key: val for key, val in found_items.items() if not re.search(r'\d', key)}

    if len(found_items) == 0:
        warn(f"No matching variable found for search terms: {search_terms} and variable_type: {variable_type}.")
    elif len(found_items) > 1 and one_item:
        warn(f"Multiple matching variables found for search terms: {search_terms} and variable_type: {variable_type}: {list(found_items.keys())}. Using the first one: {list(found_items.keys())[0]}")
        found_items = {list(found_items.keys())[0]: found_items[list(found_items.keys())[0]]}
    return found_items


def extract_value_ns(var_dict):

    keys = list(var_dict.keys())
    if len(keys) == 0:
        raise ValueError("No matching variable found in var_dict.")
    elif len(keys)  == 1:
        key = keys[0]
    else:
        warn(f"Multiple matching variables found: {keys}. Using the first one: {keys[0]}")
        key = keys[0]
    value_ns = var_dict[key][0] # Convert to seconds
    return value_ns

def extract_datetime(spl_dict):
    date = spl_dict.get('DATE', None) # ASCI date format MM/DD/YY
    time = spl_dict.get('TIME', None) # ASCI time format HH:MM:SS
    if date and time:
        datetime_str = f"{date} {time}"
        try:
            datetime_obj = datetime.strptime(datetime_str, "%m/%d/%y %H:%M:%S")
            return datetime_obj
        except ValueError:
            warn(f"Could not parse date and time from SPL parameters: {datetime_str}")
            return None
    else:
        warn("Date or time not found in SPL parameters.")
        return None
    

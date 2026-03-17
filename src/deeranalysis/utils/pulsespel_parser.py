import re
from warnings import warn, catch_warnings, simplefilter

def PulseSpelDef_to_dict(def_text):
    """
    Converts a pulse spel definition file into a dictionary

    Parameters:
    def_text: str

    Returns:
    --------
    dict

    """
    lines = def_text.split("\n")
    lines = [line.strip() for line in lines]
    # remove lines starting with ;
    if len(lines) < 2:
        warn("PulseSpel definition text is too short or empty.")
        return {}
    lines = [line for line in lines if not line.startswith(';')]
    def_lines = [line for line in lines if r'=' in line]
    match_pattern = re.compile(r'^(\w+)\s*=\s*(.*?)(;.*)?$')
    key_def_comment = [match_pattern.match(line).groups() for line in def_lines]
    def_dict = {key: (value.strip(), comment.strip() if comment else '') for key, value, comment in key_def_comment}
    return def_dict

# Search for specific terms in comments
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
    value_ns = float(var_dict[key][0]) # Convert to seconds
    return value_ns
    


def parse_PulseSpel(def_text):
    """
    Extracts the key infomation for DEER from a PulseSpel defintion file
    
    Returns
    -------
    dict:
        With 'tau1','tau2' etc...
    """
    if def_text is None or def_text.strip() == '':
        warn("No PulseSpel definition text found.")
        return {}
    var_dict = PulseSpelDef_to_dict(def_text)
    tau1_dict = search_variable(var_dict, 'tau1', 'delay',one_item=True)
    tau1 = extract_value_ns(tau1_dict)
    
    tau2_dict = search_variable(var_dict, 'tau2', 'delay',one_item=True)
    tau2 = extract_value_ns(tau2_dict)
    deadtime_dict = search_variable(var_dict, ['deadtime','zerotime','tmin'], 'delay',one_item=True)
    deadtime = extract_value_ns(deadtime_dict)

    return {'tau1': tau1,
            'tau2': tau2,
            'deadtime': deadtime}



class Parser:
    """
    The base class for all parsers. 

    This class takes the input file and extracts metadata.

    Extracted Metadata includes:
    - Experiment type (3pDEER, 4pDEER, 5pDEER, 4pRIDME, DQC, SIFTER, etc.
    - Pulse lengths (list of pulse lengths in microseconds)
    - Interpulse delays (list of interpulse delays in microseconds)

    """

    def __init__(self):
        
        pass


def match_exp_name(EXPSlct):
    """
    Matches the experiment name from EXPSlct to the corresponding parameters in PlsSPELPrgTxt.
    - `4pDEER` <- '4pDEER','four-pulse DEER', '4-pulse DEER', '4 pulse DEER', '4pPELDOR', 'four-pulse PELDOR', '4-pulse PELDOR', '4 pulse PELDOR'
    - `5pDEER` <- '5pDEER','five-pulse DEER', '5-pulse DEER', '5 pulse DEER',  '5pPELDOR', 'five-pulse PELDOR', '5-pulse PELDOR', '5 pulse PELDOR'
    - `3pDEER` <- '3pDEER','three-pulse DEER', '3-pulse DEER', '3 pulse DEER', '3pPELDOR', 'three-pulse PELDOR', '3-pulse PELDOR', '3 pulse PELDOR'
    - `4pRIDME` <- '4pRIDME','four-pulse RIDME', '4-pulse RIDME', '4 pulse RIDME'
    - `sifter` <- 'sifter','SIFTER'
    - `DQC` <- 'DQC','Double Quantum Coherence'

    Parameters
    ----------
    EXPSlct : string
        Experiment name from PlsSPELEXPSlct.
    Returns
    -------
    string or None
        Standardized experiment name or None if no match is found.
    """
    EXPSlct = EXPSlct.lower()
    EXPSlct = EXPSlct.replace(' ','')
    EXPSlct = EXPSlct.replace('-','')
    EXPSlct.replace('peldor','deer')


    if EXPSlct.lower() in ['4pdeer','four-pulse deer', '4pulsedeer']:
        return '4pDEER'
    elif EXPSlct.lower() in ['5pdeer','five-pulse deer', '5pulse deer']:
        return '5pDEER'
    elif EXPSlct.lower() in ['3pdeer','three-pulse deer', '3pulse deer']:
        return '3pDEER'
    elif EXPSlct.lower() in ['4pridme','four-pulse ridme', '4pulse ridme']:
        return '4pRIDME'
    elif EXPSlct.lower() in ['sifter']:
        return 'sifter'
    elif EXPSlct.lower() in ['dqc','double quantum coherence']:
        return 'DQC'
    else:
        return None
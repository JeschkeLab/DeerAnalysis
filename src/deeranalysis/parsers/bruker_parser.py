from parser import Parser, match_exp_name

def load_files(dsc_content, dta_content):
    """"""

class BrukerParser(Parser):
    """A parser for metadata from Bruker EPR data files, BES3T files."""

    def __init__(self,**files):

        
        super().__init__()
        self.metadata = metadata
        DSL = metadata['DSL']
        ftEpr = DSL['ftEpr']
        PlsSPELGlbTxt = ftEpr['PlsSPELGlbTxt']
        PlsSPELEXPSlct = ftEpr['PlsSPELEXPSlct']
        PlsSPELPrgTxt = ftEpr['PlsSPELPrgTxt']

        DESC = metadata['DESC']
        TITL = DESC['TITL']

        self.name = TITL if TITL else 'Unknown Bruker Experiment'
        self.exp_type = match_exp_name(PlsSPELEXPSlct)
        self.delays = self.extract_pulse_delays()
        self.meta = {}

    # def load_files(dsc_content, dta_content):


    
    def read_PulseSpel_defs(self):
        metadata = self.metadata
        DSL = metadata['DSL']
        ftEpr = DSL['ftEpr']
        PlsSPELGlbTxt = ftEpr['PlsSPELGlbTxt']
        PlsSPELEXPSlct = ftEpr['PlsSPELEXPSlct']
        PlsSPELPrgTxt = ftEpr['PlsSPELPrgTxt']

        lines = PlsSPELGlbTxt.split(r'\n') # Split the text into lines
        # remove empty lines
        lines = [line for line in lines if line.strip() != '']
        # remove lines starting with ;
        lines = [line for line in lines if not line.strip().startswith(';')]
                

    
    def extract_pulse_delays(self):
        """ Extract pulse delays from metadata.

        Returns
        -------
        delays : list
            List of pulse delays in nanoseconds.
        """


from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, LargeBinary, inspect, text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os



Base = declarative_base()

fit_global_datasets = Table('fit_global_datasets', Base.metadata,
    Column('fit_id', Integer, ForeignKey('fits.id', ondelete='CASCADE'), primary_key=True),
    Column('dataset_id', Integer, ForeignKey('datasets.id', ondelete='CASCADE'), primary_key=True)
)

fit_siblings = Table('fit_siblings', Base.metadata,
    Column('fit_id', Integer, ForeignKey('fits.id', ondelete='CASCADE'), primary_key=True),
    Column('sibling_fit_id', Integer, ForeignKey('fits.id', ondelete='CASCADE'), primary_key=True)
)
class Dataset(Base):
    __tablename__ = 'datasets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    project = Column(String, nullable=False)
    sample = Column(String, nullable=False)
    t = Column(JSON, nullable=False) # Time axis
    V = Column(JSON, nullable=False) # Signal
    V_im = Column(JSON, nullable=False,default={}) # Signal
    exp = Column(String, default='Unknown') # 4pDEER, 5pDEER, etc.
    delays = Column(JSON, default={})
    meta = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    fits = relationship("Fit", back_populates="dataset", cascade="all, delete-orphan", lazy='joined')

    @property
    def n_fits(self):
        return len(self.fits) if self.fits else 0

class Fit(Base):
    __tablename__ = 'fits'
    
    id = Column(Integer, primary_key=True)
    # Basic Info
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=False)
    name = Column(String, nullable=False)
    engine = Column(String, nullable=False) # 'DeerLab' or 'DeerNet'\
    dist_model = Column(JSON, nullable=True, default=None) # Model description for parametric fits
    bg_model = Column(String, nullable=True, default=None) # Background model name
    
    # Time domain data
    t = Column(JSON, nullable=False) # Fitted data model time axis
    model = Column(JSON, nullable=False) # Fitted data model

    # Distance domain data
    r = Column(JSON,nullable=False) # r axis for the distance distribution
    P_model = Column(JSON, nullable=False) # Distance distribution model for all models
    PUncert = Column(JSON, nullable=False) # Uncertainty model for P


    gof = Column(JSON, nullable=True) # Goodness-of-fit metrics
    dist_stats = Column(JSON, nullable=True) # Distance distribution stats (mean, median, etc.)

    fit_type = Column(String, nullable=False) # 'parametric', 'non-parametric', 'AI'
    pathways = Column(JSON, nullable=False)  # List of integers (1-10) used in the fit
    model_description = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    fit_results = Column(JSON, nullable=True) # Fitted model, residuals, stats
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    dataset = relationship("Dataset", back_populates="fits")



class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    logs_url = Column(String, nullable=True, default=None)
    logs_api_key = Column(String, nullable=True,default=None)
    DeerLab_fit_options = Column(JSON, nullable=True, default={})
    DeerNet_model_path = Column(String, nullable=True, default=None)
    
# Database setup
# db_path = 'sqlite:///deeranalysis.db'
# engine = create_engine(db_path)
# Session = sessionmaker(bind=engine)
engine = None
Session = None

def check_db_exists(folder=None):
    if folder:
        db_file = os.path.join(folder, 'deeranalysis.db')
        return os.path.exists(db_file)
    else:
        return os.path.exists('deeranalysis.db')
    
def update_schema():
    """Automatically add missing columns to existing tables"""
    inspector = inspect(engine)
    existing_table_names = inspector.get_table_names()
    
    Base.metadata.create_all(engine)  # safe — only creates missing tables

    with engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_table_names:
                continue
                
            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
            
            for column in table.columns:
                if column.name not in existing_columns:
                    col_type = column.type.compile(engine.dialect)
                    default = f"DEFAULT {column.default.arg}" if column.default else ""
                    nullable = "NOT NULL" if not column.nullable else ""
                    
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {nullable} {default}"
                    conn.execute(text(sql))
                    print(f"Added column: {table_name}.{column.name}")
        
        conn.commit()

def init_db(path=None):
    if path is None:
        db_file = 'deeranalysis.db'
    else:
        db_file = os.path.join(path, 'deeranalysis.db')
    global engine, Session
    engine = create_engine(f'sqlite:///{db_file}')
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    update_schema()

def reset_db():
    global engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
def get_session():
    global Session
    return Session()

def check_delays(dataset):
    """Checks that for a given dataset, the entries in the delay column cover 
    the requirements. E.g. for 4p DEER we need tau1, tau2 and deadtime and for 
    5pDEER we need tau1, tau2, tau3 and deadtime."""

    if dataset.exp == '4pDEER':
        required_delays = ['tau1', 'tau2', 'deadtime']
    elif dataset.exp == '5pDEER':
        required_delays = ['tau1', 'tau2', 'tau3', 'deadtime']
    elif dataset.exp == '3pDEER':
        required_delays = ['tau1', 'deadtime']
    elif dataset.exp == 'RIDME':
        required_delays = ['tau1', 'tau2', 'deadtime']
    else:
        return True, []  # No specific requirements for unknown experiment types
    
    # Add any missing delays with default values (e.g. 0)
    missing_delays = []
    new_delays = dataset.delays.copy() if dataset.delays else {}
    for delay in required_delays:
        if delay not in dataset.delays:
            new_delays[delay] = 0
            missing_delays.append(delay)
    dataset.delays = new_delays
    print(f"Checked delays for dataset {dataset.id}: missing {missing_delays}")


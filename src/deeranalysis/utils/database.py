from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os

Base = declarative_base()

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
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=False)
    name = Column(String, nullable=False)
    engine = Column(String, nullable=False) # 'DeerLab' or 'DeerNet'
    model = Column(JSON, nullable=False) # Fitted data model
    P_model = Column(JSON, nullable=False) # Distance distribution model for all models
    fit_type = Column(String, nullable=False) # 'parametric', 'non-parametric', 'AI'
    dist_model = Column(JSON, nullable=True, default=None) # Model description for parametric fits
    bg_model = Column(String, nullable=True, default=None) # Background model name
    pathways = Column(JSON, nullable=False)  # List of integers (1-10) used in the fit
    model_description = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    fit_results = Column(JSON, nullable=True) # Fitted model, residuals, stats
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    dataset = relationship("Dataset", back_populates="fits")

# Database setup
db_path = 'sqlite:///deeranalysis.db'
engine = create_engine(db_path)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session()

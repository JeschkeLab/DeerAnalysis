import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from test_deerlab_normal import make_4pdeer_dataset
from deeranalysis.utils.deerlab_options import fit_to_dict,plotly_deerlab
from deeranalysis.utils.deernet import *

class TestDeerNetFitting:

    @pytest.fixture(scope="class")
    def fit(self):
        return deernet2(make_4pdeer_dataset(), model_size=512)

    def test_returns_fit_object(self, fit):
            assert fit is not None
            assert isinstance(fit, dl.FitResult)
    
    def test_fit_to_dict(self, fit):
        fit_dict = fit_to_dict(fit)
        assert isinstance(fit_dict, dict)
        assert fit_dict['bg_model'] == 'Neural Network'
        assert fit_dict['fit_type'] == 'Neural Network'
        assert fit_dict['engine'] == 'DeerNet'
        assert fit_dict['pathways'] == [1]
        
    def test_plot_returns_figure(self, fit):
        import plotly.graph_objects as go
        fig = plotly_deerlab(fit)
        assert isinstance(fig, go.Figure)

    def test_plot_time_domain_data(self, fit):
        fig = plotly_deerlab(fit)
        trace_names = [t.name for t in fig.data]
        assert 'Data' in trace_names
        assert 'Model' in trace_names
        assert 'Background' in trace_names
        data_trace = next(t for t in fig.data if t.name == 'Data')
        assert data_trace.mode == 'markers'
        assert len(data_trace.y) > 0

    def test_plot_pr(self, fit):
        fig = plotly_deerlab(fit)
        trace_names = [t.name for t in fig.data]
        assert 'P(r)' in trace_names
        pr_trace = next(t for t in fig.data if t.name == 'P(r)')
        assert len(pr_trace.y) > 0

    def test_plot_pr_uncertainty(self, fit):
        fig = plotly_deerlab(fit)
        ci_traces = [t for t in fig.data if t.name == '95% CI']
        assert len(ci_traces) > 0
        fill_traces = [t for t in fig.data if t.fill == 'tonexty']
        assert len(fill_traces) > 0

    def test_plot_fit_and_background(self, fit):
        """Test model fit and background traces using a dict-based input."""

        fit_dict = fit_to_dict(fit)
        fig = plotly_deerlab(fit_dict)
        trace_names = [tr.name for tr in fig.data]

        assert 'Data' in trace_names
        assert 'Model' in trace_names
        assert 'Background' in trace_names
        assert 'P(r)' in trace_names
        assert '95% CI' in trace_names

        model_trace = next(tr for tr in fig.data if tr.name == 'Model')
        assert len(model_trace.y) > 0

        bg_trace = next(tr for tr in fig.data if tr.name == 'Background')
        assert len(bg_trace.y) > 0

        
"""
Test the generation of warnings after bad fitting results.

"""


import numpy as np
import pytest
import xarray as xr
import deerlab as dl

from deeranalysis.utils.deerlab_normal import deerlab_background_only, deerlab_fitting
from deeranalysis.utils.deerlab_population import deerlab_population_fitting
from deeranalysis.utils.deerlab_options import background_models, fit_to_dict
from deeranalysis.utils.deerlab_fitwarnings import (
    check_fit_results, Chi2Warning)

from test_deerlab_population import datasets as population_datasets

from test_deerlab_normal import make_4pdeer_dataset, make_bg_only_dataset


class TestDeerLabWarning4pDEER:

    @pytest.fixture(scope="class")
    def fit(self):
        return deerlab_fitting(make_4pdeer_dataset(), compactness=False)

    @pytest.fixture(scope="class")
    def fit_compact(self):
        return deerlab_fitting(make_4pdeer_dataset(), compactness=True)


    def test_unfitted_parameter_warning(self, fit):
        pass


class TestDeerLabWarningPopulation:

    @pytest.fixture(scope="class")
    def fit(self, population_datasets):
        return deerlab_population_fitting(population_datasets, n_pops=2, pathways=[1], bg_model=dl.bg_hom3d, r=np.linspace(1.5,6,100))

    @pytest.fixture(scope="class")
    def fit_bad(self, population_datasets):
        return deerlab_population_fitting(population_datasets, n_pops=2, pathways=[1], bg_model=dl.bg_hom3d, r=np.linspace(1.5,6,100), lin_maxiter=1,max_nfev=1)
    
    def test_unfitted_parameter_warning_good(self, fit):

        fit_warnings = check_fit_results(fit, fit.Vmodel)

        assert isinstance(fit_warnings, list)
        assert len(fit_warnings) == 0

    def test_unfitted_parameter_warning_bad(self, fit_bad):

        fit_warnings = check_fit_results(fit_bad, fit_bad.Vmodel)

        assert isinstance(fit_warnings, list)
        assert len(fit_warnings) > 0
        # One chi-squared warning per dataset of the global fit
        chi2_warnings = [w for w in fit_warnings if isinstance(w, Chi2Warning)]
        assert len(chi2_warnings) == 2



class TestDeerLabWarningBackground:

    @pytest.fixture(scope="class")
    def fit(self):
        return deerlab_background_only(make_bg_only_dataset('bg_hom3d',params_override={'lam':0.3}), bg_model=dl.bg_hom3d)

    @pytest.fixture(scope="class")
    def fit_bad(self):
        return deerlab_background_only(make_bg_only_dataset('bg_hom3d',params_override={'lam':0.3}), bg_model=dl.bg_hom3d, lin_maxiter=1,max_nfev=1)
    
    def test_unfitted_parameter_warning_good(self, fit):

        fit_warnings = check_fit_results(fit, fit.Bmodel)

        assert isinstance(fit_warnings, list)
        assert len(fit_warnings) == 0

    def test_unfitted_parameter_warning_bad(self, fit_bad):

        fit_warnings = check_fit_results(fit_bad, fit_bad.Bmodel)

        assert isinstance(fit_warnings, list)
        assert len(fit_warnings) > 0
        # One chi-squared warning per dataset of the global fit
        chi2_warnings = [w for w in fit_warnings if isinstance(w, Chi2Warning)]
        assert len(chi2_warnings) == 1
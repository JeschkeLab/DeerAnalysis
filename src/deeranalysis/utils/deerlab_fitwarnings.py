"""
Warnings raised after inspecting a DeerLab fit result.

Each warning carries the key details of one specific problem with a fit
(the offending value, the parameter name, the thresholds that were crossed)
together with a ``title``, a human readable ``message`` and a severity
``level``, so that a message box can be built directly from the warning
object::

    for warning in check_fit_results(fit, model):
        card = warning_card(warning)          # uses .title / .message / .level

Every warning is one of two levels:

``WarningLevel.MODERATE``
    The fit is usable but should be treated with care.
``WarningLevel.CRITICAL``
    The fit, or at least the affected parameter, should not be trusted.

The thresholds that separate the two levels live on the warning classes as
class attributes, so they can be tuned in one place, and each class provides a
``check`` classmethod that returns either a warning instance or ``None``.
"""

from enum import Enum
import numpy as np


class WarningLevel(str, Enum):
    """Severity of a fit warning."""

    MODERATE = "moderate"
    CRITICAL = "critical"

    @property
    def severity(self):
        """Integer rank, so warnings can be sorted worst-first."""
        return 2 if self is WarningLevel.CRITICAL else 1


MODERATE = WarningLevel.MODERATE
CRITICAL = WarningLevel.CRITICAL

#: Warning classes by name, filled in by ``FitWarning.__init_subclass__`` and
#: used by :meth:`FitWarning.from_dict` to restore the right class.
_WARNING_TYPES = {}


class FitWarning(Warning):
    """
    Base class for all fit warnings.

    Attributes
    ----------
    title : str
        Short heading for the message box.
    message : str
        Full explanation, ready to be displayed to the user.
    level : WarningLevel
        Either ``MODERATE`` or ``CRITICAL``.
    details : dict
        The raw values behind the warning (parameter name, fitted value,
        thresholds, ...) for tooltips, logs or the database.
    """

    title = "Fit Warning"
    level = WarningLevel.MODERATE

    def __init__(self, message, *, title=None, level=None, details=None):
        self.message = message
        if title is not None:
            self.title = title
        if level is not None:
            self.level = WarningLevel(level)
        self.details = dict(details) if details else {}
        super().__init__(message)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _WARNING_TYPES[cls.__name__] = cls

    @property
    def is_critical(self):
        return self.level is WarningLevel.CRITICAL

    def to_dict(self):
        """Serialisable form of the warning, e.g. for storage or callbacks."""
        return {
            "type": type(self).__name__,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data):
        """
        Rebuild a warning from the output of :meth:`to_dict`.

        The class named by ``data["type"]`` is restored, falling back to the
        class this is called on if the name is unknown. The stored values are
        taken as they are rather than being recomputed, so a warning read back
        from the database says exactly what it said when it was raised, even if
        the thresholds have since been changed.
        """
        klass = _WARNING_TYPES.get(data.get("type"), cls)
        details = dict(data.get("details") or {})
        warning = klass.__new__(klass)
        # Bypass the subclass constructors: they expect the fitted quantities,
        # which are recovered from ``details`` below.
        FitWarning.__init__(
            warning,
            data["message"],
            title=data.get("title"),
            level=data.get("level"),
            details=details,
        )
        for key, value in details.items():
            setattr(warning, key, value)
        return warning

    def __str__(self):
        return f"{self.title}: {self.message}"

    def __repr__(self):
        return f"{type(self).__name__}({self.level.value!r}, {self.message!r})"


_WARNING_TYPES[FitWarning.__name__] = FitWarning


# -----------------------------------------------------------------------------
# Goodness-of-fit warnings
# -----------------------------------------------------------------------------

class StatWarning(FitWarning):
    """
    Base class for all statistical warnings.

    Goodness-of-fit statistics are reported per dataset, so these warnings
    carry the number of the dataset they belong to. ``dataset`` is ``None``
    for a fit of a single dataset, and 1-based for a global fit, matching the
    ``_1``, ``_2``, ... suffixes DeerLab gives the per-dataset parameters.
    """

    def __init__(self, message, *, dataset=None, level=None, details=None):
        self.dataset = dataset
        title = self.title if dataset is None else f"{self.title} (Dataset {dataset})"
        details = dict(details) if details else {}
        details.setdefault("dataset", dataset)
        super().__init__(message, title=title, level=level, details=details)


class Chi2Warning(StatWarning):
    """Warning for high reduced chi-squared values."""

    title = "High Reduced Chi-Squared Value"
    moderate_above = 1.5
    critical_above = 3.0

    def __init__(self, chi2red, dataset=None):
        self.chi2red = float(chi2red)
        level = CRITICAL if self.chi2red >= self.critical_above else MODERATE
        if level is CRITICAL:
            message = (
                f"The reduced chi-squared value is {self.chi2red:.3f}. "
                "The model cannot describe the data; the fit should not be used."
            )
        else:
            message = (
                f"The reduced chi-squared value is {self.chi2red:.3f}, above the "
                f"expected value of 1. The model may not fully describe the data."
            )
        super().__init__(
            message,
            dataset=dataset,
            level=level,
            details={
                "chi2red": self.chi2red,
                "moderate_above": self.moderate_above,
                "critical_above": self.critical_above,
            },
        )

    @classmethod
    def check(cls, chi2red, dataset=None):
        """Return a :class:`Chi2Warning` if ``chi2red`` is too high, else ``None``."""
        if chi2red is None or not np.isfinite(chi2red):
            return None
        return cls(chi2red, dataset=dataset) if chi2red > cls.moderate_above else None


class R2Warning(StatWarning):
    """Warning for low R-squared values."""

    title = "Low R-Squared Value"
    moderate_below = 0.90
    critical_below = 0.70

    def __init__(self, r2, dataset=None):
        self.r2 = float(r2)
        level = CRITICAL if self.r2 <= self.critical_below else MODERATE
        if level is CRITICAL:
            message = (
                f"The R-squared value is {self.r2:.3f}. The fit does not follow the "
                "data and should not be used."
            )
        else:
            message = (
                f"The R-squared value is {self.r2:.3f}, below the expected "
                f"{self.moderate_below:.2f}. The fit does not follow the data closely."
            )
        super().__init__(
            message,
            dataset=dataset,
            level=level,
            details={
                "r2": self.r2,
                "moderate_below": self.moderate_below,
                "critical_below": self.critical_below,
            },
        )

    @classmethod
    def check(cls, r2, dataset=None):
        """Return an :class:`R2Warning` if ``r2`` is too low, else ``None``."""
        if r2 is None or not np.isfinite(r2):
            return None
        return cls(r2, dataset=dataset) if r2 < cls.moderate_below else None


# -----------------------------------------------------------------------------
# Parameter warnings
# -----------------------------------------------------------------------------

class ParameterWarning(FitWarning):
    """Base class for all warnings concerning a single fitted parameter."""

    title = "Parameter Warning"

    def __init__(self, parameter_name, message, *, title=None, level=None, details=None):
        self.parameter_name = parameter_name
        details = dict(details) if details else {}
        details.setdefault("parameter_name", parameter_name)
        super().__init__(message, title=title, level=level, details=details)


class UnfittedParameterWarning(ParameterWarning):
    """
    Warning for a parameter that had no influence on the fit.

    Identified from a zero column in the Jacobian: the residuals do not change
    when the parameter changes, so its value is not determined by the data.
    """

    title = "Unfitted Parameter"
    level = CRITICAL

    def __init__(self, parameter_name, value=None):
        self.value = value
        value_str = f" (reported as {value:.4g})" if value is not None else ""
        message = (
            f"Parameter '{parameter_name}'{value_str} had no effect on the fit. "
            "Its value is not determined by the data and carries no meaning."
        )
        super().__init__(parameter_name, message, details={"value": value})
    
    @classmethod
    def check(cls, parameter_name, value, std):
        """Return an :class:`UnfittedParameterWarning` if the parameter was unfitted."""
        if std is None:
            return None
        # ``std`` comes back from DeerLab as an array, one entry per element of
        # the parameter, so reduce it rather than testing it for truth.
        if np.all(np.asarray(std) == 0):
            return cls(parameter_name, value)
        return None



class ParameterBoundsWarning(ParameterWarning):
    """
    Warning for a parameter that ended the fit sitting on one of its bounds.

    A parameter pinned at a bound means the optimiser wanted to move further
    than it was allowed to, so the reported value is set by the bound and not
    by the data.
    """

    title = "Parameter At Its Bounds"
    level = CRITICAL
    #: Relative distance below which a value counts as sitting on a bound.
    tolerance = 1e-3

    def __init__(self, parameter_name, value, lower_bound, upper_bound, bound=None):
        self.value = float(value)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.bound = bound or self._which_bound(self.value, lower_bound, upper_bound)
        bound_value = lower_bound if self.bound == "lower" else upper_bound
        message = (
            f"Parameter '{parameter_name}' is pinned at its {self.bound} bound "
            f"({bound_value:.4g}) within the range ({lower_bound:.4g}, "
            f"{upper_bound:.4g}). Its value is set by the bound, not by the data."
        )
        super().__init__(
            parameter_name,
            message,
            details={
                "value": self.value,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "bound": self.bound,
            },
        )

    @classmethod
    def _which_bound(cls, value, lower_bound, upper_bound):
        return "lower" if abs(value - lower_bound) <= abs(value - upper_bound) else "upper"

    @classmethod
    def _at_bound(cls, value, bound, span):
        return abs(value - bound) <= cls.tolerance * span

    @classmethod
    def check(cls, parameter_name, value, lower_bound, upper_bound):
        """Return a :class:`ParameterBoundsWarning` if ``value`` sits on a bound."""
        if value is None or not np.isfinite(value):
            return None
        if lower_bound is None or upper_bound is None:
            return None
        if not (np.isfinite(lower_bound) and np.isfinite(upper_bound)):
            return None
        span = abs(upper_bound - lower_bound) or 1.0
        for bound, bound_value in (("lower", lower_bound), ("upper", upper_bound)):
            if cls._at_bound(value, bound_value, span):
                return cls(parameter_name, value, lower_bound, upper_bound, bound=bound)
        return None


class ParameterUncertaintyWarning(ParameterWarning):
    """
    Warning for a parameter whose uncertainty is large compared to its value.

    ``uncertainty`` is the half-width of the confidence interval, as obtained
    from the covariance matrix.
    """

    title = "Uncertain Parameter"
    #: Relative uncertainty (uncertainty / |value|) above which to warn.
    moderate_above = 0.5
    critical_above = 1.0

    def __init__(self, parameter_name, value, uncertainty, title=None,level=None):
        self.value = value
        self.uncertainty = uncertainty
        self.relative_uncertainty = self._relative(value, uncertainty)
        rel = self.relative_uncertainty
        unbounded = rel is None or not np.isfinite(rel)
        if level is None:
            level = CRITICAL if unbounded or rel >= self.critical_above else MODERATE
        if unbounded:
            message = (
                f"The uncertainty of parameter '{parameter_name}' could not be "
                "bounded. Its value should not be interpreted."
            )
        else:
            message = (
                f"Parameter '{parameter_name}' is {value:.4g} ± {uncertainty:.4g} "
                f"({rel:.0%} of its value). "
                + (
                    "Its value is not meaningfully determined by the data."
                    if level is CRITICAL
                    else "Its value is only loosely determined by the data."
                )
            )
        super().__init__(
            parameter_name,
            message,
            title=title,
            level=level,
            details={
                "value": value,
                "uncertainty": uncertainty,
                "relative_uncertainty": rel,
                "moderate_above": self.moderate_above,
                "critical_above": self.critical_above,
            },
        )

    @staticmethod
    def _relative(value, uncertainty):
        if uncertainty is None or not np.isfinite(uncertainty):
            return float("inf")
        if value is None or not np.isfinite(value) or value == 0:
            return float("inf")
        return abs(uncertainty / value)

    @classmethod
    def check(cls, parameter_name, value, uncertainty):
        """Return a warning if the relative uncertainty is too large, else ``None``."""
        if uncertainty is None:
            return None
        rel = cls._relative(value, uncertainty)
        if not np.isfinite(rel) or rel > cls.moderate_above:
            return cls(parameter_name, value, uncertainty)
        return None


class ConcUncertaintyWarning(ParameterUncertaintyWarning):
    """Warning for a spin concentration with a large uncertainty."""

    title = "Uncertain Spin Concentration"

    def __init__(self, value, uncertainty, parameter_name="conc"):
        super().__init__(parameter_name, value, uncertainty, title=self.title,level=WarningLevel.MODERATE)

    @classmethod
    def check(cls, value, uncertainty, parameter_name="conc"):
        """Return a :class:`ConcUncertaintyWarning` if the uncertainty is too large."""
        if uncertainty is None:
            return None
        rel = cls._relative(value, uncertainty)
        if not np.isfinite(rel) or rel > cls.moderate_above:
            return cls(value, uncertainty, parameter_name=parameter_name)
        return None


# -----------------------------------------------------------------------------
# Helpers for the GUI
# -----------------------------------------------------------------------------

def count_by_level(warnings):
    """
    Count warnings per level.

    Returns a ``dict`` with the keys ``"critical"`` and ``"moderate"``, ready
    for ``number_of_warnings_card``.
    """
    counts = {level.value: 0 for level in WarningLevel}
    for warning in warnings:
        counts[WarningLevel(warning.level).value] += 1
    return counts


def sort_by_level(warnings):
    """Return the warnings ordered worst-first, keeping the original order within a level."""
    return sorted(warnings, key=lambda w: -WarningLevel(w.level).severity)


#: Parameters skipped by :func:`check_fit_results`, because they are nuisance
#: parameters rather than a fitted quantity the user would act on.
SKIPPED_PARAMETERS = ('P', 'P_scale' 'scale')


def _named(param_name, names):
    """
    Whether ``param_name`` is one of ``names``.

    A global fit suffixes the parameters that are not linked across datasets,
    so ``'P_scale_2'`` counts as ``'P_scale'``.
    """
    return any(param_name == name or param_name.startswith(f'{name}_') for name in names)


def check_fit_results(fit_result, fit_model):
    """
    Check the fit results for any warnings and returns a list of Warnings.

    Handles both a fit of a single dataset and a global fit of several: the
    goodness-of-fit statistics are checked per dataset, and the warnings of a
    global fit name the dataset they belong to.

    The checks that pass are dropped, and the warnings that remain are ordered
    worst-first, so the result can be handed straight to the GUI.

    Parameters
    ----------
    fit_result : DeerLab FitResult
        The result of a DeerLab fit, either a single fit or a global fit.
    fit_model : DeerLab Model
        The model that was fitted, or ``None`` if the model is not available for DeerNet fits. In this case, only goodness-of-fit statistics are checked.
    """
    warnings = [w for w in _iter_fit_checks(fit_result, fit_model) if w is not None]
    return sort_by_level(warnings)


def _iter_fit_checks(fit_result, fit_model):
    """
    Run every check against the fit result.

    Yields one result per check, which is ``None`` whenever the check passed;
    :func:`check_fit_results` filters those out.
    """

    # A global fit reports one set of statistics per dataset, a single fit one
    # dict for the one dataset it fitted.
    stats = fit_result.stats
    if isinstance(stats, dict):
        stats = [stats]
    for dataset, stat in enumerate(stats, start=1):
        # Only number the datasets when there is more than one to tell apart.
        dataset = dataset if len(stats) > 1 else None
        if 'chi2red' in stat:
            yield Chi2Warning.check(stat['chi2red'], dataset=dataset)
        if 'R2' in stat:
            yield R2Warning.check(stat['R2'], dataset=dataset)

    if not fit_model is None:
        for param_name in fit_result.paramlist:
            param_name = str(param_name)
            if _named(param_name, SKIPPED_PARAMETERS):
                continue

            pUncert = getattr(fit_result, f"{param_name}Uncert", None)
            pModel = getattr(fit_model, param_name, None)
            pValue = getattr(fit_result, param_name)

            # The distance distribution and any other vector-valued parameter hold
            # one value per distance point, not a single fitted quantity.
            if np.size(pValue) > 1:
                continue

            if pUncert is not None:
                yield UnfittedParameterWarning.check(param_name, pValue, pUncert.std)

            if pModel is not None:
                yield ParameterBoundsWarning.check(param_name, pValue, pModel.lb, pModel.ub)

            if pModel is not None and pUncert is not None:
                # Half-width of the 95% confidence interval
                pm_ci = np.max(np.abs(pUncert.ci(95) - pValue))
                if _named(param_name, ('conc',)):
                    yield ConcUncertaintyWarning.check(pValue, pm_ci, parameter_name=param_name)
                else:
                    yield ParameterUncertaintyWarning.check(param_name, pValue, pm_ci)

    

def warnings_to_dict(warnings):
    """
    Convert a list of warnings to a serialisable form.

    Returns a ``list`` of ``dict``s, each one the output of
    :meth:`FitWarning.to_dict`.
    """
    return [w.to_dict() for w in warnings]

def warnings_from_dict(data):
    """
    Rebuild a list of warnings from the output of :func:`warnings_to_dict`.

    Returns a ``list`` of :class:`FitWarning` instances.
    """
    return [FitWarning.from_dict(w) for w in data]
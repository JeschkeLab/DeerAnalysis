"""ScientificNumberInput – a dmc.TextInput that displays extreme numbers in sci notation.

Renders values whose absolute magnitude is < 1e-3 or >= 1e6 as  "1.23 E-6"
(mantissa space E sign exponent).  All other values are shown as plain decimals.

Re-formatting and step-button behaviour are handled client-side by
assets/scinotation.js.

Usage
-----
    from deeranalysis.components.scientific_number_input import (
        ScientificNumberInput, parse_sci, format_sci,
    )

    # In a layout:
    ScientificNumberInput(value=5.3e-7, id="my-input", suffix=" µM", step=1e-8)

    # In a callback reading the value back (value is a string):
    @callback(Output(...), Input("my-input", "value"))
    def cb(raw):
        number = parse_sci(raw)   # -> float or None
        ...
"""
import math

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

_SCI_LOWER = 1e-3
_SCI_UPPER = 1e6

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def format_sci(value) -> str | None:
    """Format *value* as a string, switching to sci notation at extreme magnitudes."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(v):
        return str(v)
    if v == 0:
        return "0"
    abs_v = abs(v)
    if abs_v < _SCI_LOWER or abs_v >= _SCI_UPPER:
        exp = int(math.floor(math.log10(abs_v)))
        mantissa = round(v / 10 ** exp, 2)
        sign = "+" if exp >= 0 else ""
        return f"{mantissa:g} E{sign}{exp}"
    return f"{v:g}"


def parse_sci(text) -> float | None:
    """Parse a number string; accepts plain floats and '1.23 E-6' / '1.23e-6' forms."""
    if text is None or str(text).strip() == "":
        return None
    normalised = str(text).replace(" ", "").upper().replace("E+", "e").replace("E-", "e-").replace("E", "e")
    try:
        return float(normalised)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _step_section(suffix: str | None):
    """Build the stacked ▲/▼ spinner controls (+ optional suffix text)."""
    btn_base = {
        "cursor": "pointer",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "flex": "1",
        "paddingInline": "3px",
        "userSelect": "none",
        "color": "var(--mantine-color-dimmed)",
        "lineHeight": "1",
    }
    # Spinner: fixed 20 px wide, never shrinks, always on the right edge.
    spinner = html.Div(
        [
            html.Div(
                DashIconify(icon="mdi:chevron-up", width=11),
                className="sci-num-btn sci-num-btn-up",
                style=btn_base,
            ),
            html.Div(
                DashIconify(icon="mdi:chevron-down", width=11),
                className="sci-num-btn sci-num-btn-down",
                style=btn_base,
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "height": "100%",
            "width": "20px",
            "flexShrink": "0",
            "borderLeft": "1px solid var(--mantine-color-default-border)",
        },
    )
    if not suffix:
        return spinner
    return html.Div(
        [
            html.Span(
                suffix,
                style={
                    "flex": "1",
                    "minWidth": "0",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                    "fontSize": "var(--input-fz, var(--mantine-font-size-sm))",
                    "color": "var(--mantine-color-dimmed)",
                },
            ),
            spinner,
        ],
        style={
            "display": "flex",
            "alignItems": "stretch",
            "height": "100%",
            "width": "100%",
            "gap": "6px",
        },
    )


# ---------------------------------------------------------------------------
# Component factory
# ---------------------------------------------------------------------------

def ScientificNumberInput(value=None, id=None, step="auto", suffix=None,
                          min=None, max=None, **kwargs):
    """A dmc.TextInput pre-formatted for scientific notation with step arrows.

    Parameters
    ----------
    value : float | int | None
        Numeric value.  Displayed as '1.23 E-6' when |value| < 1e-3 or >= 1e6.
    id : any
        Dash component id, forwarded unchanged to the TextInput.
    step : float | "auto"
        Arrow increment.  ``"auto"`` (default) increments by one order of magnitude
        below the current value (e.g. value=5e-7 → step=1e-7).
    suffix : str | None
        Optional unit label shown to the left of the arrows (e.g. ``" µM"``).
    min, max : float | None
        Optional bounds enforced by the step buttons.
    **kwargs
        All other dmc.TextInput props (size, label, disabled, …).
    """
    existing_input_props = kwargs.pop("inputProps", {}) or {}
    tagged_input_props = {
        **existing_input_props,
        "data-scinotation": "true",
        "data-step": str(step),
        **({"data-min": str(min)} if min is not None else {}),
        **({"data-max": str(max)} if max is not None else {}),
    }

    # Let the browser measure the content; arrows are pinned at a fixed 20 px
    # so they're always visible regardless of suffix length.
    right_section_width = "fit-content" if suffix else 22

    return dmc.TextInput(
        value=format_sci(value),
        id=id,
        inputProps=tagged_input_props,
        rightSection=_step_section(suffix),
        rightSectionWidth=right_section_width,
        rightSectionPointerEvents="all",
        **kwargs,
    )

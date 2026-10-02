# Elements for displaying fitwarnings in the GUI. 

import dash_mantine_components as dmc
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback, MATCH, ALL, ALLSMALLER
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_fitwarnings import check_fit_results, warnings_to_dict, warnings_from_dict,FitWarning

def warning_card(warning):
    if issubclass(type(warning), FitWarning):
        warning_title = warning.title
        warning_message = warning.message
        level = warning.level
    elif isinstance(warning, dict):
        warning_title = warning.get('title', 'Warning')
        warning_message = warning.get('message', 'This is a warning message.')
        level = warning.get('level', 'moderate')
    else:
        raise ValueError("Warning must be a FitWarning instance or a dictionary.")
    if level == 'critical':
        card_color = "#F8D7DA"
        card_icon = DashIconify(icon="mdi:alert-circle-outline", width=36, color="#721C24")
    else:
        card_color = "#FFF3CD"
        card_icon = DashIconify(icon="mdi:alert-circle-outline", width=36, color="#856404")
    # warning_title = dmc.Text("Conc Parameter Warning", c="#856404",fw=700)
    # warning_message = dmc.Text("This is a warning message.", c="#856404")

    card = dmc.Card(
        children=[
            dmc.Group(
                children=[
                    dmc.Box(card_icon, style={"flexShrink": 0}),
                    dmc.Stack(
                        children=[
                            dmc.Text(warning_title, c="#856404",fw=700),
                            dmc.Text(warning_message, c="#856404")
                        ],
                        gap="xs",
                        style={"flex": 1, "minWidth": 0},
                    )
                ],
                gap="xs",
                align="flex-start",
                wrap="nowrap",
            )
        ],
        shadow="sm",
        p="md", 
        style={"backgroundColor": card_color, "borderRadius": "8px"}
    )
    return card


def number_of_warnings_children(critical, moderate, page_id):
    """
    Children of the number of warnings card, so that ``update_overview_cards``
    can re-render them when the fit results change.

    ``critical`` and ``moderate`` are the counts, or ``None`` when the fit has
    not been checked for warnings, which is shown as "–".
    """
    title = "Warnings"

    critical_color = "red"
    moderate_color = "orange"

    expand_button = dmc.ActionIcon(
        DashIconify(icon="mdi:arrow-expand", width=20, color="gray"),
        variant="transparent",
        size="lg",
        id={"type": "n_warnings_overview-expand-button", "page": page_id},
    )

    def _count(n):
        return "–" if n is None else f"{n}"

    value_line = dmc.Group(
        [
            dmc.Tooltip(DashIconify(icon="mdi:alert-circle-outline", width=20, color=critical_color),label="Critical Warnings", position="top", withArrow=True),
            dmc.Text(_count(critical), size="xl", fw=700, c=critical_color),
            dmc.Tooltip(DashIconify(icon="mdi:alert-outline", width=20, color=moderate_color),label="Moderate Warnings", position="top", withArrow=True),
            dmc.Text(_count(moderate), size="xl", fw=700, c=moderate_color),
        ],
        align="center",
        justify="center"
    )

    return [
        dmc.Box([
            dmc.Text(title, size="lg", fw=700, ta="center"),
            dmc.Box(expand_button, style={"position": "absolute", "top": 0, "right": 0}),
            ],
            style={"position": "relative"}
        ),
        value_line,
    ]


def number_of_warnings_card(critical, moderate, page_id):
    """
    based on fit_page_components overview_card

    Shares the ``overview-card`` id type with the other overview cards, under
    the metric ``"warnings"``, so that ``update_overview_cards`` updates it.
    """
    return dmc.Paper(
            number_of_warnings_children(critical, moderate, page_id),
            id={"type": "overview-card", "metric": "warnings", "page": page_id},
            withBorder=True,
            p="md",
            style={"textAlign": "center", "minWidth": 120},
        )

    

def list_of_warnings_card(warnings):

    scroll_area_children = []
    for warning in warnings:
        card = warning_card(warning)
        scroll_area_children.append(card)


    return dmc.ScrollArea(
        dmc.Stack(scroll_area_children, gap="md"),
        mah=400,
        scrollbars="y",
        type="auto",
    )



def list_of_warnings_modal(page_id):

    children = dmc.Text("No warnings to display.", c="gray", size="md")
    modal = dmc.Modal(
        title="Warnings",
        id={"type": "n_warnings_overview-modal", "page": page_id},
        size="80%",
        children=[
            html.Div(children, style={"maxHeight": "400px", "overflowY": "auto"},id={"type": "n_warnings_overview-modal-content", "page": page_id}),
        ],
        centered=False,
        overlayProps={"opacity": 0.55, "blur": 3},
    )

    return modal

@callback(
    Output({"type": "n_warnings_overview-modal-content", "page": MATCH}, "children"),
    Input({"type": "n_warnings_overview-expand-button", "page": MATCH}, "n_clicks"),
    State({"type": "fit-results-store", "page": MATCH}, "data"),
    State({"type": "fit-results-store-multi", "page": MATCH}, "data"),
    prevent_initial_call=True,
)
def update_warnings_modal_content(n_, fit_results_store, fit_results_store_multi):
    # Every fit page renders both stores (single-fit pages use a dummy multi store),
    # so a single callback handles both and prefers the multi store when populated.
    if fit_results_store_multi is not None:
        fit_results_store = fit_results_store_multi
    if fit_results_store is None:
        return dash.no_update
    warnings = warnings_from_dict(fit_results_store.get('warnings', []))

    if len(warnings) == 0:
        children = dmc.Text("No warnings to display.", c="gray", size="md")
    else:
        children = list_of_warnings_card(warnings)

    return children


@callback(
    Output({"type": "n_warnings_overview-modal", "page": MATCH}, "opened"),
    Input({"type": "n_warnings_overview-expand-button", "page": MATCH}, "n_clicks"),
    State({"type": "n_warnings_overview-modal", "page": MATCH}, "opened"),
    prevent_initial_call=True,
)
def open_warnings_modal(n_, opened):

    if n_:
        return not opened
    return opened

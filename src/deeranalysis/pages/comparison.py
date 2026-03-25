import dash
from dash import html, dcc, callback, Input, Output, State, ALL
import numpy as np
from deeranalysis.utils.database import get_session, Dataset, Fit
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from deeranalysis.components.fit_finder import fit_select
from deeranalysis.components.dataset_search_model import create_dataset_modal, search_fit_modal
from deeranalysis.utils.deerlab_options import plotly_comparison, colour_scheme_dark, colour_scheme_light

dash.register_page(__name__)

PAGE_ID = 'comparison'
N_SLOTS = 3

# AppShell: header=60, footer=40, padding="md"=16px top+bottom → 60+40+32 = 132 ≈ 140px
_PAGE_HEIGHT = 'calc(100vh - 140px)'

layout = html.Div([
    # ── Hidden: modals & drawer ────────────────────────────────────────────
    create_dataset_modal(PAGE_ID),
    search_fit_modal(),

    dmc.Drawer(
        id='comp-options-drawer',
        title="Plot Options",
        position="right",
        size="sm",
        padding="md",
        zIndex=1000,
        children=[
            dmc.Stack([
                dmc.Text("Vertical Offset", size="sm", fw=500),
                dmc.Slider(
                    id='comp-voffset-slider',
                    min=0, max=1.0, step=0.05, value=0.3,
                    marks=[
                        {"value": 0,   "label": "0"},
                        {"value": 0.5, "label": "0.5"},
                        {"value": 1.0, "label": "1"},
                    ],
                    mb="xl",
                ),
                dmc.Divider(my="sm"),
                dmc.Select(
                    id='comp-ci-select',
                    label="Uncertainty Interval",
                    data=[
                        {'label': '50%', 'value': '50'},
                        {'label': '68%', 'value': '68'},
                        {'label': '90%', 'value': '90'},
                        {'label': '95%', 'value': '95'},
                        {'label': '99%', 'value': '99'},
                    ],
                    value='95',
                    comboboxProps={"withinPortal": False},
                ),
                dmc.Divider(my="sm"),
                dmc.Switch(
                    id='comp-show-ci-toggle',
                    label="Show Uncertainty Bands",
                    checked=True,
                ),
            ], gap="md"),
        ],
    ),

    # ── Top bar: title + burger ────────────────────────────────────────────
    dmc.Group([
        dmc.Title("Comparison", order=2),
        dmc.ActionIcon(
            DashIconify(icon='material-symbols:menu', width=22),
            id='comp-burger-btn',
            size="lg",
            variant="subtle",
        ),
    ], justify="space-between", mb="xs"),
    dmc.Divider(mb="xs"),

    # ── Dataset / fit selection (colour-coded) ─────────────────────────────
    dmc.Paper(
        dmc.Group(
            [
                fit_select(page_id=PAGE_ID, index=str(i), color=colour_scheme_dark[i - 1])
                for i in range(1, N_SLOTS + 1)
            ],
            align="flex-start",
            grow=True,
        ),
        p="sm", mb="xs", withBorder=True,
        style={'flexShrink': '0'},
    ),

    # ── Main comparison plot (fills remaining space) ───────────────────────
    dmc.Paper(
        dcc.Graph(
            id='comp-plot',
            figure=plotly_comparison(None),
            style={'height': '100%', 'width': '100%'},
            config={'responsive': True,
                    'toImageButtonOptions': {'format': 'svg'},}
            # useResizeHandler=True,
        ),
        p="xs", mb="xs", withBorder=True,
        style={'flex': '1', 'minHeight': '0'},
    ),

    # ── Statistics (collapsible, default open) ─────────────────────────────
    dmc.Paper([
        dmc.Group([
            dmc.Text("Statistics", fw=600, size="md"),
            dmc.ActionIcon(
                DashIconify(icon='material-symbols:keyboard-arrow-down', width=20),
                id='comp-stats-toggle-btn',
                size="sm",
                variant="subtle",
            ),
        ], justify="space-between", mb=4),
        dmc.Collapse(
            id='comp-stats-collapse',
            opened=True,
            children=[
                html.Div(
                    id='comp-stats-table',
                    style={'overflowY': 'auto', 'maxHeight': '200px'},
                ),
            ],
        ),
    ], p="sm", withBorder=True, style={'flexShrink': '0'}),

], style={
    'display': 'flex',
    'flexDirection': 'column',
    'height': _PAGE_HEIGHT,
    'overflow': 'hidden',
    'gap': '4px',
})


# ── Callbacks ───────────────────────────────────────────────────────────────

@callback(
    Output('comp-options-drawer', 'opened'),
    Input('comp-burger-btn', 'n_clicks'),
    State('comp-options-drawer', 'opened'),
    prevent_initial_call=True,
)
def toggle_options_drawer(n_clicks, opened):
    return not opened


@callback(
    Output('comp-stats-collapse', 'opened'),
    Input('comp-stats-toggle-btn', 'n_clicks'),
    State('comp-stats-collapse', 'opened'),
    prevent_initial_call=True,
)
def toggle_stats(n_clicks, opened):
    return not opened


@callback(
    Output({'type': 'dataset-dropdown', 'page': PAGE_ID, 'index': ALL}, 'data'),
    Input('url', 'pathname'),
)
def update_dataset_dropdowns(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return [options] * N_SLOTS


@callback(
    Output({'type': 'fit-dropdown', 'page': PAGE_ID, 'index': ALL}, 'data'),
    Input({'type': 'dataset-dropdown', 'page': PAGE_ID, 'index': ALL}, 'value'),
)
def update_fit_dropdowns(dataset_ids):
    def get_options(dataset_id):
        if not dataset_id:
            return []
        session = get_session()
        fits = session.query(Fit).filter_by(dataset_id=dataset_id).all()
        options = [{'label': fit.name, 'value': str(fit.id)} for fit in fits]
        session.close()
        return options
    return [get_options(did) for did in dataset_ids]


@callback(
    Output('comp-plot', 'figure'),
    Output('comp-stats-table', 'children'),
    Input({'type': 'fit-dropdown', 'page': PAGE_ID, 'index': ALL}, 'value'),
    Input('comp-voffset-slider', 'value'),
    Input('comp-ci-select', 'value'),
    Input('comp-show-ci-toggle', 'checked'),
)
def compare_fits(fit_ids, offset, ci_str, show_ci):
    ci = int(ci_str) if ci_str else 95

    session = get_session()
    loaded = []
    for fid in fit_ids:
        if not fid:
            continue
        fit = session.query(Fit).filter_by(id=fid).first()
        if fit:
            loaded.append((fit.dataset, fit))
    session.close()

    data_dicts = [_fit_to_dict(ds, fit) for ds, fit in loaded]
    titles = [f"Dataset {i+1}" for i in range(len(data_dicts))]

    fig = plotly_comparison(data_dicts if data_dicts else None,
                            titles=titles, offset=offset, ci=ci, show_ci=show_ci)
    fig.update_layout(title=None)

    stats = _build_stats_tables(data_dicts, titles)
    return fig, stats


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fit_to_dict(dataset, fit):
    out = {}
    out['t'] = np.array(dataset.t, dtype=float)
    out['V'] = np.array(dataset.V, dtype=float)
    out['V'] /= out['V'].max()
    out['model'] = np.array(fit.model, dtype=float)
    out['r'] = np.array(fit.r, dtype=float)
    out['P'] = np.array(fit.P_model, dtype=float)
    out['model_t'] = np.array(fit.t, dtype=float)
    try:
        out['PUncert'] = np.array(fit.PUncert, dtype=float) if fit.PUncert is not None else None
    except Exception:
        out['PUncert'] = None
    return out


TIME_METRICS   = ["SNR (dB)", "Modulation Depth", "RMSD"]
DIST_METRICS   = ["Mean Distance (nm)", "Std Distance (nm)"]


def _compute_stat(metric, dd):
    try:
        V     = dd['V']
        model = dd['model']
        r     = dd['r']
        P     = dd['P']
        if metric == "SNR (dB)":
            noise = np.std(V - model)
            return f"{20 * np.log10(1.0 / noise):.1f}" if noise > 0 else "∞"
        elif metric == "Modulation Depth":
            return f"{float(np.max(model) - np.min(model)):.4f}"
        elif metric == "RMSD":
            return f"{np.sqrt(np.mean((V - model) ** 2)):.4f}"
        elif metric == "Mean Distance (nm)":
            dr = r[1] - r[0]
            norm = np.sum(P * dr)
            return f"{np.sum(r * P * dr) / norm:.3f}" if norm > 0 else "N/A"
        elif metric == "Std Distance (nm)":
            dr   = r[1] - r[0]
            norm = np.sum(P * dr)
            if norm <= 0:
                return "N/A"
            mean_r = np.sum(r * P * dr) / norm
            return f"{np.sqrt(np.sum((r - mean_r) ** 2 * P * dr) / norm):.3f}"
    except Exception:
        pass
    return "N/A"


def _make_dmc_table(metrics, data_dicts, titles, section_title):
    """Build a single dmc.Table for a given list of metrics."""
    # Header row: "Metric" + one cell per dataset
    header_cells = [dmc.TableTh("Metric")]
    for i, title in enumerate(titles):
        swatch = html.Span(style={
            'display': 'inline-block', 'width': '10px', 'height': '10px',
            'borderRadius': '2px', 'backgroundColor': colour_scheme_dark[i],
            'marginRight': '5px', 'verticalAlign': 'middle',
        })
        header_cells.append(dmc.TableTh([swatch, title]))

    body_rows = []
    for metric in metrics:
        cells = [dmc.TableTd(dmc.Text(metric, size="sm", fw=500))]
        for dd in data_dicts:
            cells.append(dmc.TableTd(dmc.Text(_compute_stat(metric, dd), size="sm")))
        body_rows.append(dmc.TableTr(cells))

    return dmc.Stack([
        dmc.Text(section_title, size="sm", fw=600, c="dimmed"),
        dmc.Table(
            [
                dmc.TableThead(dmc.TableTr(header_cells)),
                dmc.TableTbody(body_rows),
            ],
            striped=True,
            highlightOnHover=True,
            withColumnBorders=True,
            withTableBorder=True,
            fz="sm",
        ),
    ], gap="xs")


def _build_stats_tables(data_dicts, titles):
    if not data_dicts:
        return dmc.Text("No fits selected.", c="dimmed", size="sm")

    time_table = _make_dmc_table(TIME_METRICS, data_dicts, titles, "Time Domain")
    dist_table = _make_dmc_table(DIST_METRICS, data_dicts, titles, "Distance Domain")

    return dmc.SimpleGrid(
        [time_table, dist_table],
        cols=2,
        spacing="md",
    )



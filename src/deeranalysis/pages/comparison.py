import dash
from dash import html, dcc, callback, Input, Output, State, ALL, ctx
import numpy as np
from deeranalysis.utils.database import get_session, Dataset, Fit
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from deeranalysis.components.fit_finder import fit_select
from deeranalysis.components.dataset_search_model import create_dataset_modal, search_fit_modal
from deeranalysis.utils.deerlab_options import plotly_comparison, colour_scheme_dark, colour_scheme_light


from deerlab import UQResult
dash.register_page(__name__)

PAGE_ID = 'comparison'
N_SLOTS_MAX = 5
N_SLOTS_DEFAULT = 3

# AppShell: header=60, footer=40, padding="md"=16px top+bottom → 60+40+32 = 132 ≈ 140px
_PAGE_HEIGHT = 'calc(100vh - 140px)'

layout = html.Div([
    dcc.Store(id='comp-n-slots', data=N_SLOTS_DEFAULT),

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
    dmc.Paper([
        dmc.SimpleGrid(
            [
                html.Div(
                    fit_select(page_id=PAGE_ID, index=str(i), color=colour_scheme_dark[i - 1]),
                    id={'type': 'slot-wrapper', 'index': str(i)},
                    style={} if i <= N_SLOTS_DEFAULT else {'display': 'none'},
                )
                for i in range(1, N_SLOTS_MAX + 1)
            ],
            id='comp-fit-grid',
            cols={'base': 2, 'sm': 3, 'xl': N_SLOTS_MAX},
        ),
        dmc.Group([
            dmc.ActionIcon(
                DashIconify(icon='material-symbols:remove', width=16),
                id='comp-remove-slot-btn',
                size="sm", variant="subtle",
                disabled=True,
            ),
            dmc.Text(
                id='comp-slot-count', size="xs", c="dimmed",
                children=f"{N_SLOTS_DEFAULT} / {N_SLOTS_MAX}",
            ),
            dmc.ActionIcon(
                DashIconify(icon='material-symbols:add', width=16),
                id='comp-add-slot-btn',
                size="sm", variant="subtle",
            ),
        ], gap="xs", justify="flex-end", mt="xs"),
    ], p="sm", mb="xs", withBorder=True, style={'flexShrink': '0'}),

    # ── Main comparison plot (fills remaining space) ───────────────────────
    dmc.Paper(
        dcc.Graph(
            id='comp-plot',
            figure=plotly_comparison(None),
            style={'height': '100%', 'width': '100%'},
            config={'responsive': True,
                    'toImageButtonOptions': {'format': 'svg'},}
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
    Output('comp-n-slots', 'data'),
    Input('comp-add-slot-btn', 'n_clicks'),
    Input('comp-remove-slot-btn', 'n_clicks'),
    State('comp-n-slots', 'data'),
    prevent_initial_call=True,
)
def update_slot_count(add_clicks, remove_clicks, n):
    if ctx.triggered_id == 'comp-add-slot-btn':
        return min(n + 1, N_SLOTS_MAX)
    if ctx.triggered_id == 'comp-remove-slot-btn':
        return max(n - 1, N_SLOTS_DEFAULT)
    return n


@callback(
    Output({'type': 'slot-wrapper', 'index': ALL}, 'style'),
    Output('comp-fit-grid', 'cols'),
    Output('comp-add-slot-btn', 'disabled'),
    Output('comp-remove-slot-btn', 'disabled'),
    Output('comp-slot-count', 'children'),
    Input('comp-n-slots', 'data'),
)
def update_slots_visibility(n):
    styles = [{} if i + 1 <= n else {'display': 'none'} for i in range(N_SLOTS_MAX)]
    cols = {'base': 2, 'sm': min(n, 3), 'xl': n}
    return styles, cols, n >= N_SLOTS_MAX, n <= N_SLOTS_DEFAULT, f"{n} / {N_SLOTS_MAX}"


@callback(
    Output({'type': 'dataset-dropdown', 'page': PAGE_ID, 'index': ALL}, 'data'),
    Input('url', 'pathname'),
)
def update_dataset_dropdowns(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return [options] * N_SLOTS_MAX


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
    Input('comp-n-slots', 'data'),
    Input('comp-voffset-slider', 'value'),
    Input('comp-ci-select', 'value'),
    Input('comp-show-ci-toggle', 'checked'),
)
def compare_fits(fit_ids, n_slots, offset, ci_str, show_ci):
    ci = int(ci_str) if ci_str else 95
    fit_ids = fit_ids[:n_slots]

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
                            titles=titles, offset=offset, ci=ci, show_ci=show_ci,
                            show_bg=True,)
    fig.update_layout(title=None)

    stats = _build_stats_tables(data_dicts, titles, n_slots)
    return fig, stats


# ── Helpers ──────────────────────────────────────────────────────────────────

def _convert_lists_in_dicts_to_arrays(d):
    """Recursively convert lists in a dict to numpy arrays."""
    if isinstance(d, dict):
        return {k: _convert_lists_in_dicts_to_arrays(v) for k, v in d.items()}
    elif isinstance(d, list):
        return np.array(d)
    else:
        return d

def _fit_to_dict(dataset, fit):
    out = {}
    out['t'] = np.array(dataset.t, dtype=float)
    out['V'] = np.array(dataset.V, dtype=float)
    out['V'] /= out['V'].max()
    out['model_t'] = np.array(fit.t, dtype=float)
    out['dist_stats'] = fit.dist_stats or {}
    out['gof'] = fit.gof or {}

    background_only = getattr(fit, 'fit_type', None) == 'background'

    if background_only:
        out['model'] = None
        out['r'] = None
        out['P'] = None
        out['PUncert'] = None
        bg_data = fit.background if hasattr(fit, 'background') and fit.background is not None else fit.model
        out['background'] = np.array(bg_data, dtype=float) if bg_data is not None else None
    else:
        out['model'] = np.array(fit.model, dtype=float) if fit.model is not None else None
        out['r'] = np.array(fit.r, dtype=float) if fit.r is not None else None
        out['P'] = np.array(fit.P_model, dtype=float) if fit.P_model is not None else None
        out['background'] = np.array(fit.background, dtype=float) if hasattr(fit, 'background') and fit.background is not None else None
        if isinstance(fit.PUncert, dict):
            PUncert = UQResult.from_dict(_convert_lists_in_dicts_to_arrays(fit.PUncert))
            out['PUncert'] = PUncert
        else:
            out['PUncert'] = None
    return out


TIME_METRICS = ["SNR", "MND", "RMSD"]
KEY_STATS = ['mean', 'median', 'mode', 'std', 'iqr', 'skewness', 'kurtosis']
STAT_LABELS = {
    'mean':     'Mean (nm)',
    'median':   'Median (nm)',
    'mode':     'Mode (nm)',
    'std':      'Std. Dev. (nm)',
    'iqr':      'IQR (nm)',
    'skewness': 'Skewness',
    'kurtosis': 'Kurtosis',
}

TIME_LABELS = {
    'SNR': 'SNR',
    'MNR': 'MNR',
    'rmsd': 'RMSD',
    'R2': 'R²',}

def _compute_stat(metric, dd):
    try:
        V     = dd['V']
        model = dd['model']
        if metric == "SNR":
            noise = np.std(V - model)
            return f"{20 * np.log10(1.0 / noise):.1f}" if noise > 0 else "∞"
        elif metric == "Modulation Depth":
            return f"{float(np.max(model) - np.min(model)):.4f}"
        elif metric == "RMSD":
            return f"{np.sqrt(np.mean((V - model) ** 2)):.4f}"
    except Exception as e:
        print(f"Error computing {metric} for dataset. {e}")
        pass
    return "N/A"


def _format_dist_stat(entry):
    """Format a dist_stats entry {'value': float, 'ci': [lb, ub] | None} as a string."""
    if entry is None:
        return "N/A"
    elif isinstance(entry, (int, float)):
        return f"{entry:.3f}"
    elif isinstance(entry,str):
        return entry
    else:
        val = f"{entry['value']:.3f}"
        if entry.get('ci'):
            lb, ub = entry['ci']
            return f"{val} [{lb:.3f}, {ub:.3f}]"
        return val


def _header_cells(titles):
    cells = [dmc.TableTh("Metric")]
    for i, title in enumerate(titles):
        swatch = html.Span(style={
            'display': 'inline-block', 'width': '10px', 'height': '10px',
            'borderRadius': '2px', 'backgroundColor': colour_scheme_dark[i],
            'marginRight': '5px', 'verticalAlign': 'middle',
        })
        cells.append(dmc.TableTh([swatch, title]))
    return cells


def _make_time_table(data_dicts, titles):
    body_rows = []

    for key in TIME_LABELS:
        label = TIME_LABELS[key]
        cells = [dmc.TableTd(dmc.Text(label, size="sm", fw=500))]
        for dd in data_dicts:
            entry = dd.get('gof', {}).get(key,'N/A')
            cells.append(dmc.TableTd(dmc.Text(_format_dist_stat(entry), size="sm")))
        body_rows.append(dmc.TableTr(cells))

    return dmc.Stack([
        dmc.Text("Time Domain", size="sm", fw=600, c="dimmed"),
        dmc.Table(
            [dmc.TableThead(dmc.TableTr(_header_cells(titles))), dmc.TableTbody(body_rows)],
            striped=True, highlightOnHover=True, withColumnBorders=True, withTableBorder=True, fz="sm",
        ),
    ], gap="xs")


def _make_dist_table(data_dicts, titles):
    body_rows = []

    for key in KEY_STATS:
        label = STAT_LABELS[key]
        cells = [dmc.TableTd(dmc.Text(label, size="sm", fw=500))]
        for dd in data_dicts:
            entry = dd.get('dist_stats', {}).get(key)
            cells.append(dmc.TableTd(dmc.Text(_format_dist_stat(entry), size="sm")))
        body_rows.append(dmc.TableTr(cells))

    return dmc.Stack([
        dmc.Text("Distance Domain", size="sm", fw=600, c="dimmed"),
        dmc.Table(
            [dmc.TableThead(dmc.TableTr(_header_cells(titles))), dmc.TableTbody(body_rows)],
            striped=True, highlightOnHover=True, withColumnBorders=True, withTableBorder=True, fz="sm",
        ),
    ], gap="xs")


_STATS_SPLIT_BREAKPOINT = {1: 'xs', 2: 'sm', 3: 'md', 4: 'lg', 5: 'xl'}

def _build_stats_tables(data_dicts, titles, n_slots=N_SLOTS_DEFAULT):
    if not data_dicts:
        return dmc.Text("No fits selected.", c="dimmed", size="sm")

    bp = _STATS_SPLIT_BREAKPOINT.get(n_slots, 'xl')
    return dmc.SimpleGrid(
        [_make_time_table(data_dicts, titles), _make_dist_table(data_dicts, titles)],
        cols={'base': 1, bp: 2},
        spacing="md",
    )

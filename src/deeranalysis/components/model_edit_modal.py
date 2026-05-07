import numpy as np
import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, no_update, MATCH, ALL, ctx
import deerlab as dl
from dash_iconify import DashIconify


exp_model_links = {
    '3pDEER': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.ex_3pdeer.html',
    '4pDEER': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.ex_4pdeer.html',
    '5pDEER': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.ex_fwd5pdeer.html',
    'dqc': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.ex_dqc.html',
    'ridme': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.ex_ridme.html',
}

b_model_links = {
    'bg_hom3d': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.bg_hom3d.html',
    'bg_exp': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.bg_exp.html',
}

p_model_links = {
    'dd_gauss':      'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_gauss.html',
    'dd_gauss2':     'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_gauss2.html',
    'dd_gauss3':     'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_gauss3.html',
    'dd_rice':       'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_rice.html',
    'dd_rice2':      'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_rice2.html',
    'dd_rice3':      'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_rice3.html',
    'dd_gengauss':   'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_gengauss.html',
    'dd_skewgauss':  'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_skewgauss.html',
    'dd_wormchain':  'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_wormchain.html',
    'dd_wormcgauss': 'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_wormcgauss.html',
    'dd_randcoil':   'https://jeschkelab.github.io/DeerLab/_autosummary/deerlab.dd_randcoil.html',
}


def model_link_buttons(exp_type, bg_model, p_model):
    def make_btn(label, href):
        btn = dmc.Button(label, variant="outline", size="xs",
                         leftSection=DashIconify(icon='material-symbols:link', width=16),
                         disabled=not bool(href))
        if href:
            return dmc.Anchor(btn, href=href, target="_blank", underline="never")
        return btn

    return [
        make_btn("Experiment Model", exp_model_links.get(exp_type)),
        make_btn("Background Model", b_model_links.get(bg_model)),
        make_btn("Distance Distribution Model", p_model_links.get(p_model)),
    ]


def _make_bound_input(value, bound_id, step, suffix, precision):
    """NumberInput paired with an ∞ toggle button for lb/ub fields."""
    is_inf = value is None
    inf_label = "−∞" if bound_id['type'] == 'param-lb' else "+∞"
    toggle_id = {
        'type': 'param-inf-toggle',
        'bound': bound_id['type'],
        'name': bound_id['name'],
        'page': bound_id['page'],
    }
    return dmc.Group([
        dmc.NumberInput(
            value=None if is_inf else value,
            id=bound_id,
            size="xs", step=step, suffix=suffix, decimalScale=precision,
            disabled=is_inf,
            placeholder=inf_label if is_inf else None,
            style={"flex": 1, "minWidth": 70},
        ),
        dmc.Tooltip(
            dmc.ActionIcon(
                inf_label,
                id=toggle_id,
                size="sm",
                variant="filled" if is_inf else "light",
                color="blue",
                w='auto',
            ),
            label="Toggle between finite value and infinity",
            position="top",
            withArrow=True,
        ),
    ], gap=4, wrap="nowrap", align="center")


def create_table_row_from_dict(name, param_data, page_id):
    """Creates a table row from a serialized parameter data dict."""
    if 'reftime' in name:
        step, precision = 0.1, 2
    elif 'lam' in name:
        step, precision = 0.01, 2
    elif 'conc' in name:
        step, precision = 1.0, 2
    else:
        step, precision = 0.01, 2

    suffix = param_data.get('unit', '')

    return dmc.TableTr([
        dmc.TableTd(name),
        dmc.TableTd(dmc.NumberInput(
            value=param_data.get('par0'),
            id={'type': 'param-par0', 'name': name, 'page': page_id},
            size="xs", step=step, suffix=suffix, decimalScale=precision,
        )),
        dmc.TableTd(_make_bound_input(
            param_data.get('lb'),
            {'type': 'param-lb', 'name': name, 'page': page_id},
            step, suffix, precision,
        )),
        dmc.TableTd(_make_bound_input(
            param_data.get('ub'),
            {'type': 'param-ub', 'name': name, 'page': page_id},
            step, suffix, precision,
        )),
        dmc.TableTd(dmc.Checkbox(
            checked=param_data.get('frozen', False),
            id={'type': 'param-frozen', 'name': name, 'page': page_id},
            size="xs",
        )),
        dmc.TableTd(param_data.get('description', '')),
    ])


def create_model_edit_modal(page_id):
    table_header = dmc.TableThead(
        dmc.TableTr([
            dmc.TableTh("Name"),
            dmc.TableTh("Par0"),
            dmc.TableTh("LB"),
            dmc.TableTh("UB"),
            dmc.TableTh("Frozen"),
            dmc.TableTh("Description"),
        ])
    )

    return dmc.Modal(
        title="Edit Model Parameters",
        id={'type': 'model-edit-modal', 'page': page_id},
        size='70%',
        children=[
            dcc.Store(id={'type': 'model-store', 'page': page_id}),
            dmc.Group(
                id={'type': 'model-links-group', 'page': page_id},
                children=model_link_buttons(None, None, None),
            ),
            dmc.Table(
                id={'type': 'model-params-table', 'page': page_id},
                children=[
                    table_header,
                    dmc.TableTbody(
                        id={'type': 'model-params-tbody', 'page': page_id},
                        children=[],
                    ),
                ],
                striped=True,
                highlightOnHover=True,
            ),
            dmc.Button("Save", id={'type': 'save-model-btn', 'page': page_id}, color="blue", mt="md"),
            dmc.Text("", id={'type': 'param-save-error', 'page': page_id}, c="red", size="sm", mt="xs"),
        ],
    )


@callback(
    Output({'type': 'model-params-tbody', 'page': MATCH}, 'children'),
    Output({'type': 'model-links-group', 'page': MATCH}, 'children'),
    Input({'type': 'model-store', 'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def render_model_table(model_data):
    if not model_data or 'params' not in model_data:
        return [], []

    page_id = ctx.outputs_list[0]['id']['page']
    params = model_data['params']
    exp_type = model_data.get('exp_type')
    bg_model_name = model_data.get('bg_model')
    p_model_name = model_data.get('p_model')

    rows = [create_table_row_from_dict(name, pdata, page_id) for name, pdata in params.items()]
    links = model_link_buttons(exp_type, bg_model_name, p_model_name)
    return rows, links


def _register_inf_toggle(bound_type):
    @callback(
        Output({'type': bound_type, 'name': MATCH, 'page': MATCH}, 'disabled'),
        Output({'type': bound_type, 'name': MATCH, 'page': MATCH}, 'value'),
        Output({'type': bound_type, 'name': MATCH, 'page': MATCH}, 'placeholder'),
        Output({'type': 'param-inf-toggle', 'bound': bound_type, 'name': MATCH, 'page': MATCH}, 'variant'),
        Input({'type': 'param-inf-toggle', 'bound': bound_type, 'name': MATCH, 'page': MATCH}, 'n_clicks'),
        State({'type': bound_type, 'name': MATCH, 'page': MATCH}, 'disabled'),
        prevent_initial_call=True,
    )
    def toggle_inf(n_clicks, currently_disabled):
        placeholder = "−∞" if bound_type == 'param-lb' else "+∞"
        if currently_disabled:
            return False, 0, None, "light"
        else:
            return True, None, placeholder, "filled"

_register_inf_toggle('param-lb')
_register_inf_toggle('param-ub')


@callback(
    Output({'type': 'model-params-store', 'page': MATCH}, 'data'),
    Output({'type': 'model-edit-modal', 'page': MATCH}, 'opened', allow_duplicate=True),
    Output({'type': 'param-par0', 'name': ALL, 'page': MATCH}, 'error'),
    Output({'type': 'param-save-error', 'page': MATCH}, 'children'),
    Input({'type': 'save-model-btn', 'page': MATCH}, 'n_clicks'),
    State({'type': 'param-par0', 'name': ALL, 'page': MATCH}, 'value'),
    State({'type': 'param-lb', 'name': ALL, 'page': MATCH}, 'value'),
    State({'type': 'param-ub', 'name': ALL, 'page': MATCH}, 'value'),
    State({'type': 'param-frozen', 'name': ALL, 'page': MATCH}, 'checked'),
    prevent_initial_call=True,
)
def save_model_params(n_clicks, par0_vals, lb_vals, ub_vals, frozen_vals):
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    # Recover param names from the ALL-pattern states (par0 inputs)
    param_names = [s['id']['name'] for s in ctx.states_list[0]]

    errors = []
    for i in range(len(param_names)):
        par0 = par0_vals[i] if i < len(par0_vals) else None
        lb = lb_vals[i] if i < len(lb_vals) else None
        ub = ub_vals[i] if i < len(ub_vals) else None
        if par0 is not None and ((lb is not None and par0 < lb) or (ub is not None and par0 > ub)):
            errors.append("Must be between lb and ub")
        else:
            errors.append(False)

    if any(errors):
        return no_update, no_update, errors, "Par0 must be between lb and ub for all parameters."

    overrides = {}
    for i, name in enumerate(param_names):
        overrides[name] = {
            'par0': par0_vals[i] if i < len(par0_vals) else None,
            'lb': lb_vals[i] if i < len(lb_vals) else None,
            'ub': ub_vals[i] if i < len(ub_vals) else None,
            'frozen': frozen_vals[i] if i < len(frozen_vals) else False,
        }

    return overrides, False, [False] * len(param_names), ""

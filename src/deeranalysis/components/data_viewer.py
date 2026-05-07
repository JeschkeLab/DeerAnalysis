"""
Data Viewer component — reusable layout and callbacks for the signal viewer
used on the upload page.
"""
import dash
from dash import html, dcc, callback, Input, Output, State, MATCH
import dash_mantine_components as dmc
from dash_iconify import DashIconify

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from deerlab import correctphase
colour_scheme_dark = ['#7C37DB','#DB7C17','#166122']
colour_scheme_light = ['#A787D6',"#EDA659",'#67B875']


def data_viewer_layout(page_id, title="Dataset Viewer",correct_phase=True,masking_enabled=False, inital_figure=None):
    """
    Returns the Data Viewer section: graph with phase correction toggle,
    masking enable/disable switch, and masking controls.
    """
    switches = []
    if correct_phase:
        switches.append(
            dmc.Switch(
                id={'type': 'data-plot-correctphase', 'page': page_id},
                onLabel="ON", offLabel="OFF",
                label="Correct Phase", labelPosition='left',
                size="lg",
                checked=True,
            )
        )
    if masking_enabled:
        switches.append(
            dmc.Switch(
                id={'type': 'data-masking-enabled', 'page': page_id},
                onLabel="ON", offLabel="OFF",
                label="Masking", labelPosition='left',
                size="lg",
                checked=False,
            )
        )
    if inital_figure is None:
        inital_figure = plot_upload(None)

    return html.Div([
        dmc.Group([
            dmc.Text(title, size="md", fw=500),
            dmc.Group(switches, gap="xl"),
        ], justify="space-between", mb="xs"),

        dcc.Graph(id={'type': 'data-viewer-plot', 'page': page_id}, style={'height': '500px'},
                  figure=inital_figure),

        html.Div(
            id={'type': 'masking-controls-div', 'page': page_id},
            style={'display': 'none'},
            children=dmc.Group([
                dmc.Text("Box/lasso select points, then:", size="sm", c="dimmed"),
                dmc.Button(
                    "Mask Selected",
                    id={'type': 'mask-selected-btn', 'page': page_id},
                    color="orange",
                    size="sm",
                    variant="light",
                    leftSection=DashIconify(icon="mdi:eye-off-outline", width=16),
                ),
                dmc.Button(
                    "Clear Masks",
                    id={'type': 'clear-masks-btn', 'page': page_id},
                    color="gray",
                    size="sm",
                    variant="subtle",
                    leftSection=DashIconify(icon="mdi:close-circle-outline", width=16),
                ),
                dmc.Badge(id={'type': 'masked-count-badge', 'page': page_id}, color="orange", variant="light", size="sm"),
            ], mt="xs", mb="md"),
        ),
    ])


# ---------------------------------------------------------------------------
# Masking enable/disable — show or hide the masking controls
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'masking-controls-div', 'page': MATCH}, 'style'),
    Input({'type':'data-masking-enabled','page':MATCH}, 'checked'),
)
def toggle_masking_controls(enabled):
    if enabled:
        return {'display': 'block'}
    return {'display': 'none'}


# ---------------------------------------------------------------------------
# Mask selected points
# ---------------------------------------------------------------------------
@callback(
    Output({'type':"dataset-store",'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'mask-selected-btn', 'page': MATCH}, 'n_clicks'),
    State({'type': 'data-viewer-plot', 'page': MATCH}, 'selectedData'),
    State({'type':"dataset-store",'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def mask_selected_points(n_clicks, selected_data, dataset_store):
    """Adds box/lasso-selected points to the masked set."""
    if dataset_store is None or not selected_data:
        return dash.no_update

    current_masked = set(dataset_store.get('masked_indices', []))
    for point in selected_data.get('points', []):
        # curveNumber 0 is the Real trace (with invisible markers)
        if point.get('curveNumber') == 0:
            current_masked.add(point['pointIndex'])

    dataset_store['masked_indices'] = sorted(current_masked)
    return dataset_store


# ---------------------------------------------------------------------------
# Clear all masks
# ---------------------------------------------------------------------------
@callback(
    Output({'type':"dataset-store",'page': MATCH}, 'data', allow_duplicate=True),
    Input({'type': 'clear-masks-btn', 'page': MATCH}, 'n_clicks'),
    State({'type':"dataset-store",'page': MATCH}, 'data'),
    prevent_initial_call=True,
)
def clear_masks(n_clicks, dataset_store):
    """Removes all masked points."""
    if dataset_store is None:
        return dash.no_update
    dataset_store['masked_indices'] = []
    return dataset_store


# ---------------------------------------------------------------------------
# Masked-count badge
# ---------------------------------------------------------------------------
@callback(
    Output({'type': 'masked-count-badge', 'page': MATCH}, 'children'),
    Input({'type':"dataset-store",'page': MATCH}, 'data'),
)
def update_masked_badge(dataset_store):
    if dataset_store is None:
        return ""
    count = len(dataset_store.get('masked_indices', []))
    return f"{count} masked" if count > 0 else "0 masked"

def plot_upload(dataset,correct_phase=True,masking_enabled=False,linewidth=3,**kwargs):
    """Generates the figure for the data viewer, applying phase correction and masking as needed."""

    import xarray as xr
    import deeranalysis.utils.database as database

    fig = make_subplots(rows=1, cols=1)

    fig.update_xaxes(title_text="Time (µs)", row=1, col=1)
    fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
    if dataset is None:
        return fig
    
    if isinstance(dataset, dict):
        
        t_min = dataset.get('tmin', 0)
        t = np.array(dataset['t']) + t_min
        V = np.array(dataset['RealData']) + 1j * np.array(dataset['ImagData'])
        V = V / np.max(np.abs(V))
        masked_indices = np.array(dataset.get('masked_indices', []), dtype=int)
    elif isinstance(dataset, database.Dataset):
        t = np.array(dataset.t)
        tmin = kwargs.get('tmin',0)
        t = t - t[0] + (tmin / 1e3)
        V = np.array(dataset.V) + 1j * np.array(dataset.V_im)
        V = V / np.max(np.abs(V))

        masked_indices = kwargs.get('masked_indices', np.array([], dtype=int))
    else:
        raise ValueError(f"Unsupported dataset format for plotting.: {type(dataset)}")

    if correct_phase:
        Vre,Vim,_ = correctphase(V, full_output=True)
        V = Vre + 1j*Vim
    n = len(t)
    is_masked = np.zeros(n, dtype=bool)
    if len(masked_indices) > 0:
        is_masked[masked_indices] = True


    
    fig.add_trace(go.Scatter(x=t[~is_masked], y=V.real[~is_masked], mode='markers+lines', name='Real',
                             marker=dict(opacity=0, size=8), line=dict(color=colour_scheme_dark[0],width=linewidth)), row=1, col=1)
    if np.sum(np.abs(V.imag)) > 1e-4:  # Only plot imaginary if it's not negligible
        fig.add_trace(go.Scatter(x=t[~is_masked], y=V.imag[~is_masked], mode='lines', name='Imag', 
                                 line=dict(color=colour_scheme_dark[1],width=linewidth)), row=1, col=1)
    if masking_enabled and len(is_masked) > 0:
        fig.add_trace(go.Scatter(x=t[is_masked], y=V.real[is_masked], mode='markers', name='Masked Re', 
                                 line=dict(color=colour_scheme_light[0],width=linewidth)), row=1, col=1)
        if np.sum(np.abs(V.imag)) > 1e-4:  # Only plot imaginary if it's not negligible
            fig.add_trace(go.Scatter(x=t[is_masked], y=V.imag[is_masked], mode='markers', name='Masked Im', 
                                     line=dict(color=colour_scheme_light[1],width=linewidth)), row=1, col=1)
    return fig
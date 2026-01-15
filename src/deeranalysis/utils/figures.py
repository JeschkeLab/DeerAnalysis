
from plotly.subplots import make_subplots
import plotly.graph_objs as go

# In your callback or layout
def create_subplot_figure(layout='vertical'):
    if layout == 'vertical':
        nrows = 2
        ncols = 1
        vetical_spacing = 0.15
        horizontal_spacing = 0.0
    elif layout == 'horizontal':
        nrows = 1
        ncols = 2
        vetical_spacing = 0.0
        horizontal_spacing = 0.15
    else:
        raise ValueError("Layout must be either 'vertical' or 'horizontal'")
    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=("Time Domain", "Distance Distribution"),
        vertical_spacing=vetical_spacing,horizontal_spacing=horizontal_spacing
    )
    
    # # Add traces to first subplot (row 1)
    # fig.add_trace(
    #     go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Data 1"),
    #     row=1, col=1
    # )
    
    # # Add traces to second subplot (row 2)
    # fig.add_trace(
    #     go.Scatter(x=[1, 2, 3], y=[7, 8, 9], name="Data 2"),
    #     row=2, col=1
    # )
    
    # Update layout
    fig.update_layout(height=700, showlegend=True, legend=dict(x=0.5, y=-0.15, xanchor='center', yanchor='top', orientation='h'))
    fig.update_xaxes(title_text="Time (us)", row=1, col=1)
    fig.update_xaxes(title_text="Distance (nm)", row=2, col=1)
    fig.update_yaxes(title_text="Signal (a.u.)", row=1, col=1)
    fig.update_yaxes(title_text="Probability (nm<sup>-1</sup>)", row=2, col=1)
    
    return fig
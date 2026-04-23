import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from datetime import datetime, timedelta
import psutil
import platform
from collections import deque

dash.register_page(__name__, path='/system_monitor')

# Store historical data for graphs (last 60 minutes = 360 data points at 10-second intervals)
MAX_DATA_POINTS = 360
cpu_history = deque(maxlen=MAX_DATA_POINTS)
memory_history = deque(maxlen=MAX_DATA_POINTS)
network_sent_history = deque(maxlen=MAX_DATA_POINTS)
network_recv_history = deque(maxlen=MAX_DATA_POINTS)
time_history = deque(maxlen=MAX_DATA_POINTS)

# Initialize network counters
last_net_io = None

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g., 1253656 => 1.20MB
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

layout = html.Div([
    html.H1("System Monitor"),
    html.Hr(),
    
    # System Info
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("System Information")),
                dbc.CardBody([
                    html.P(id="system-info", children="Loading...")
                ])
            ])
        ], width=12)
    ], className="mb-3"),
    
    # Real-time metrics
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("CPU Usage")),
                dbc.CardBody([
                    html.H2(id="cpu-usage", className="text-center"),
                    html.P("Average across all cores", className="text-center text-muted")
                ])
            ], color="primary", outline=True)
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Memory Usage")),
                dbc.CardBody([
                    html.H2(id="memory-usage", className="text-center"),
                    html.P(id="memory-details", className="text-center text-muted")
                ])
            ], color="info", outline=True)
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Storage")),
                dbc.CardBody([
                    html.H2(id="storage-usage", className="text-center"),
                    html.P(id="storage-details", className="text-center text-muted")
                ])
            ], color="warning", outline=True)
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Network")),
                dbc.CardBody([
                    html.H2(id="network-usage", className="text-center", style={"fontSize": "1.2rem"}),
                    html.P(id="network-details", className="text-center text-muted", style={"fontSize": "0.8rem"})
                ])
            ], color="success", outline=True)
        ], width=3),
    ], className="mb-4"),
    
    # CPU Graph
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("CPU Usage (Last 60 Minutes)")),
                dbc.CardBody([
                    dcc.Graph(id="cpu-graph", config={'displayModeBar': False})
                ])
            ])
        ], width=12)
    ], className="mb-3"),
    
    # Memory Graph
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Memory Usage (Last 60 Minutes)")),
                dbc.CardBody([
                    dcc.Graph(id="memory-graph", config={'displayModeBar': False})
                ])
            ])
        ], width=12)
    ], className="mb-3"),
    
    # Network Graph
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Network Usage (Last 60 Minutes)")),
                dbc.CardBody([
                    dcc.Graph(id="network-graph", config={'displayModeBar': False})
                ])
            ])
        ], width=12)
    ], className="mb-3"),
    
    # Auto-refresh interval (10 seconds)
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds
        n_intervals=0
    )
])


@callback(
    [Output("system-info", "children"),
     Output("cpu-usage", "children"),
     Output("memory-usage", "children"),
     Output("memory-details", "children"),
     Output("storage-usage", "children"),
     Output("storage-details", "children"),
     Output("network-usage", "children"),
     Output("network-details", "children"),
     Output("cpu-graph", "figure"),
     Output("memory-graph", "figure"),
     Output("network-graph", "figure")],
    [Input("interval-component", "n_intervals")]
)
def update_system_monitor(n):
    global last_net_io
    
    # System Information
    uname = platform.uname()
    system_info = html.Div([
        html.P(f"System: {uname.system}"),
        html.P(f"Node Name: {uname.node}"),
        html.P(f"Release: {uname.release}"),
        html.P(f"Version: {uname.version}"),
        html.P(f"Machine: {uname.machine}"),
        html.P(f"Processor: {uname.processor if uname.processor else 'N/A'}"),
        html.P(f"Python Version: {platform.python_version()}"),
    ])
    
    # CPU Usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_usage = f"{cpu_percent}%"
    
    # Memory Usage
    svmem = psutil.virtual_memory()
    memory_usage = f"{svmem.percent}%"
    memory_details = f"{get_size(svmem.used)} / {get_size(svmem.total)}"
    
    # Storage Usage (root partition)
    disk = psutil.disk_usage('/System/Volumes/Data' if platform.system() == 'Darwin' else '/')
    storage_usage = f"{disk.percent}%"
    storage_details = f"{get_size(disk.used)} / {get_size(disk.total)}"
    
    # Network Usage
    net_io = psutil.net_io_counters()
    if last_net_io is None:
        # First run, initialize
        last_net_io = net_io
        network_usage = "Initializing..."
        network_details = f"Total: ↑{get_size(net_io.bytes_sent)} ↓{get_size(net_io.bytes_recv)}"
        net_sent_rate = 0
        net_recv_rate = 0
    else:
        # Calculate rates (bytes per second, converted to 10-second interval)
        net_sent_rate = (net_io.bytes_sent - last_net_io.bytes_sent) / 10.0  # per second
        net_recv_rate = (net_io.bytes_recv - last_net_io.bytes_recv) / 10.0  # per second
        last_net_io = net_io
        
        network_usage = f"↑{get_size(net_sent_rate)}/s ↓{get_size(net_recv_rate)}/s"
        network_details = f"Total: ↑{get_size(net_io.bytes_sent)} ↓{get_size(net_io.bytes_recv)}"
    
    # Update history
    current_time = datetime.now()
    time_history.append(current_time)
    cpu_history.append(cpu_percent)
    memory_history.append(svmem.percent)
    network_sent_history.append(net_sent_rate / (1024 * 1024))  # Convert to MB/s
    network_recv_history.append(net_recv_rate / (1024 * 1024))  # Convert to MB/s
    
    # Create graphs
    # CPU Graph
    cpu_fig = go.Figure()
    if len(time_history) > 1:
        cpu_fig.add_trace(go.Scatter(
            x=list(time_history),
            y=list(cpu_history),
            mode='lines',
            name='CPU Usage',
            line=dict(color='#0d6efd', width=2),
            fill='tozeroy',
            fillcolor='rgba(13, 110, 253, 0.2)'
        ))
    cpu_fig.update_layout(
        xaxis_title="Time",
        yaxis_title="CPU Usage (%)",
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        height=300,
        margin=dict(l=50, r=20, t=20, b=50)
    )
    
    # Memory Graph
    memory_fig = go.Figure()
    if len(time_history) > 1:
        memory_fig.add_trace(go.Scatter(
            x=list(time_history),
            y=list(memory_history),
            mode='lines',
            name='Memory Usage',
            line=dict(color='#0dcaf0', width=2),
            fill='tozeroy',
            fillcolor='rgba(13, 202, 240, 0.2)'
        ))
    memory_fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Memory Usage (%)",
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        height=300,
        margin=dict(l=50, r=20, t=20, b=50)
    )
    
    # Network Graph
    network_fig = go.Figure()
    if len(time_history) > 1:
        network_fig.add_trace(go.Scatter(
            x=list(time_history),
            y=list(network_sent_history),
            mode='lines',
            name='Upload',
            line=dict(color='#198754', width=2)
        ))
        network_fig.add_trace(go.Scatter(
            x=list(time_history),
            y=list(network_recv_history),
            mode='lines',
            name='Download',
            line=dict(color='#20c997', width=2)
        ))
    network_fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Network Speed (MB/s)",
        hovermode='x unified',
        height=300,
        margin=dict(l=50, r=20, t=20, b=50)
    )
    
    return (system_info, cpu_usage, memory_usage, memory_details, 
            storage_usage, storage_details, network_usage, network_details,
            cpu_fig, memory_fig, network_fig)

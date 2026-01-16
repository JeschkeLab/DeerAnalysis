import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output
from deeranalysis.utils.database import init_db
from dash_iconify import DashIconify
import dash_mantine_components as dmc

# Initialize database
init_db()

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP],)
server = app.server

sidebar = html.Div(
    [
        html.H2("DeerAnalysis", className="display-4"),
        html.Hr(),
        html.P(
            "Datasets", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("File Upload", href="/upload", active="exact"),
                dbc.NavLink("Logs Upload", href="/logs_upload", active="exact"),
                dbc.NavLink("Datasets", href="/", active="exact"),
                dbc.NavLink("Comparison", href="/comparison", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
        html.P(
            "DeerLab Fitting", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("autoDEER Fit", href="/autoDEER", active="exact"),
                dbc.NavLink("Non-Parametric Fit", href="/nonparametric", active="exact"),
                dbc.NavLink("Parametric Fit", href="/parametric", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
        html.P(
            "DeerNet Fitting", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("DeerNet Fit", href="/deernet", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
        html.P(
            "About", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("About DeerAnalysis", href="/about", active="exact"),
                dbc.NavLink("Citation", href="/citation", active="exact"),
                dbc.NavLink("Github 🔗", href="https://github.com/JeschkeLab", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
        html.Div(
            [
                dbc.NavLink(DashIconify(icon="mdi:cog", width=24), href="/config", active="exact"),
                dbc.NavLink(DashIconify(icon="mdi:monitor", width=24), href="/system_monitor", active="exact"),
            ],
            style={
                "position": "absolute",
                "bottom": "2rem",
                "left": "2rem",
                "display": "flex",
                "gap": "1rem",
            },
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "22rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    },
)

content = html.Div(
    dash.page_container,
    style={
        "margin-left": "22rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    },
)

footer = html.Footer(
    html.P("© 2025 DeerAnalysis. Developed by Hugo Karas, Stefan Stoll and Gunnar Jeschke. All rights reserved.", className="text-left text-muted"),
    style={
        "position": "fixed",
        "margin-left": "22rem",
        "bottom": 0,
        "width": "100%",
        "padding": "0.5rem",
        "background-color": "#f8f9fa",
        "border-top": "1px solid #dee2e6",
    },
)

app.layout = dmc.MantineProvider([dcc.Location(id="url"), sidebar, content, footer])

if __name__ == "__main__":
    app.run(debug=True)

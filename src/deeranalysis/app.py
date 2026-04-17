import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback
from deeranalysis.utils.database import init_db
from dash_iconify import DashIconify
import dash_mantine_components as dmc
import sys
import os
from pathlib import Path

from deeranalysis.components.setup_modal_desktop import create_setup_modal,default_directory
from deeranalysis.components.dmc_theme import da_dmctheme
from deeranalysis.utils.logs_plugin import initialize_logs_api,check_logs_api_key
from deeranalysis.utils.database import get_appearance_settings

import plotly.io as pio

pio.templates["compact"] = dict(
    layout=dict(
        font=dict(size=11),
        margin=dict(l=50, r=20, t=50, b=40),
        xaxis=dict(tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10)),
        legend=dict(font=dict(size=10)),
    )
)
pio.templates.default = "plotly+compact"

def first_time_setup():
    """
    Checks if the database exists.
    """
    database_dir = os.path.join(default_directory(), 'deeranalysis.db')
    # print(f"Checking for existing database at {database_dir}: {'Found' if database_dir else 'Not found'}")
    if not os.path.exists(database_dir):
        return True
    return False

# Get the correct base path for PyInstaller
if getattr(sys, 'frozen', False):
    basedir = Path(sys._MEIPASS)
    desktop_mode = True
else:
    basedir = Path(__file__).parent
    desktop_mode = False

if not first_time_setup():
    # print("Initializing database connection...")
    init_db(default_directory())
    initialize_logs_api()



app = dash.Dash(__name__,
                 use_pages=True, 
                #  pages_folder=str(basedir / 'pages'),
                #  assets_folder=str(basedir / 'assets'),
                 external_stylesheets=[dbc.themes.BOOTSTRAP, dmc.styles.ALL])
server = app.server

def get_icon(icon):
    return DashIconify(icon=icon, width=20)

def create_nav_link(label, href, icon):
    return dmc.NavLink(
        label=label,
        href=href,
        leftSection=get_icon(icon) if icon else None,
        id={"type": "nav-link", "index": href},
    )



sidebar_content = dmc.Stack(
    [
        dmc.Text("Datasets", size="sm", c="dimmed", fw=500),
        create_nav_link("File Upload", "/upload", "mdi:upload"),
        *( [create_nav_link("Logs Upload", "/logs_upload", "mdi:file-document-outline")] if check_logs_api_key() else [] ),
        create_nav_link("Datasets", "/", "mdi:database"),
        create_nav_link("Comparison", "/comparison", "mdi:compare"),
        
        dmc.Divider(my="sm"),
        
        dmc.Text("DeerLab Fitting", size="sm", c="dimmed", fw=500),

        # create_nav_link("autoDEER Fit", "/autoDEER", "mdi:auto-fix"),
        create_nav_link("Non-Parametric Fit", "/nonparametric", "mdi:chart-bell-curve-cumulative"),
        create_nav_link("Parametric Fit", "/parametric", "mdi:function-variant"),
        create_nav_link("Global Fit", "/global", "mdi:globe"),
        create_nav_link("Population Fit", "/population", "mdi:people-group"),
        
        dmc.Divider(my="sm"),
        
        dmc.Text("DeerNet Fitting", size="sm", c="dimmed", fw=500),
        create_nav_link("DeerNet Fit", "/deernet", "mdi:brain"),
        
        dmc.Divider(my="sm"),

        dmc.Text("About", size="sm", c="dimmed", fw=500),
        create_nav_link("About DeerAnalysis", "/about", "mdi:information"),
        create_nav_link("Citation", "/citation", "mdi:format-quote-close"),
        dmc.NavLink(
            label="Github",
            href="https://github.com/JeschkeLab/DeerAnalysis",
            leftSection=get_icon("mdi:github"),
            target="_blank",
            rightSection=get_icon("mdi:open-in-new"),
        ),
        dmc.NavLink(
            label="DeerLab",
            href="https://github.com/JeschkeLab/DeerLab",
            leftSection=get_icon("mdi:github"),
            target="_blank",
            rightSection=get_icon("mdi:open-in-new"),
        ),
        dmc.Space(style={"flex": 1}),
        dmc.SimpleGrid(
            [
                create_nav_link("", "/config", "mdi:cog"),
                create_nav_link("", "/system_monitor", "mdi:monitor")
            ],
            cols=4
        )
    ],
    h="100%",
    gap="xs",
    justify="space-between"
)

app.layout = dmc.MantineProvider(
    [
        dmc.NotificationContainer(id="notification-container"),
        dcc.Location(id="url"),
        dcc.Store(id="first-time-setup", data=first_time_setup()), # TODO: Change so only for desktop mode
        dcc.Store(id="desktop-mode", data=desktop_mode),
        dcc.Store(id="color-scheme-store", data=get_appearance_settings()[0] if not first_time_setup() else "light"),
        dcc.Store(id="ui-scale-store", data=get_appearance_settings()[1] if not first_time_setup() else 1.0),
        dmc.AppShell(
            [
                dmc.AppShellHeader(
                    dmc.Group(
                        [
                            dmc.Burger(id="burger", hiddenFrom="sm", size="sm"),
                            dmc.Image(src="/assets/header.svg", h=50, w="auto", fit="contain"),
                            # dmc.Title("DeerAnalysis", order=3),
                        ],
                        h="100%",
                        px="md",
                    )
                ),
                dmc.AppShellNavbar(
                    children=sidebar_content,
                    p="md",
                    id="navbar",
                ),
                dmc.AppShellMain(children=dash.page_container),
                dmc.AppShellFooter(
                    dmc.Text(
                        "© 2026 ETH Zürich, UNIGE. Developed by Hugo Karas. All rights reserved.",
                        size="xs",
                        c="dimmed"
                    ),
                    p="xs",
                    display="flex",
                    style={"alignItems": "center"}
                ),
            ],
            header={"height": 60},
            footer={"height": 40},
            navbar={
                "width": 200,
                "breakpoint": "sm",
                "collapsed": {"mobile": True},
            },
            padding="md",
            id="app-shell",
        ),
        create_setup_modal()
    ],
    theme=da_dmctheme,
    id="mantine-provider",
    forceColorScheme="light",
)


@callback(
    Output("mantine-provider", "forceColorScheme"),
    Input("color-scheme-store", "data"),
)
def update_color_scheme(color_scheme):
    return color_scheme or "light"


_BASE_FONT_SIZES = {"xs": 10, "sm": 11, "md": 12, "lg": 14, "xl": 16}
_BASE_SPACING = {"xs": 4, "sm": 6, "md": 10, "lg": 14, "xl": 18}
_BASE_HEADING_SIZES = {"h1": 2.5, "h2": 2.0, "h3": 1.5, "h4": 1.2, "h5": 1.0, "h6": 0.8}

@callback(
    Output("mantine-provider", "theme"),
    Input("ui-scale-store", "data"),
)
def update_ui_scale(scale):
    s = scale if scale is not None else 1.0
    theme = dict(da_dmctheme)
    theme["fontSizes"] = {k: f"{v * s:.1f}px" for k, v in _BASE_FONT_SIZES.items()}
    theme["spacing"] = {k: f"{v * s:.1f}px" for k, v in _BASE_SPACING.items()}
    theme["headings"] = {
        "fontWeight": "700",
        "sizes": {k: {"fontSize": f"{v * s:.3f}rem", "lineHeight": "1.2"} for k, v in _BASE_HEADING_SIZES.items()},
    }
    return theme

@callback(
    Output("setup-modal", "opened"),
    Input("first-time-setup", "data"),
    prevent_initial_call=False
)
def open_setup_modal(is_first_time):
    return is_first_time

@callback(
    Output("app-shell", "navbar"),
    Input("burger", "opened"),
    Input("ui-scale-store", "data"),
    State("app-shell", "navbar"),
)
def toggle_navbar(opened, scale, navbar):
    s = scale if scale is not None else 1.0
    navbar["width"] = round(200 * s)
    if opened is not None:
        navbar["collapsed"]["mobile"] = not opened
    return navbar

@callback(
    Output({"type": "nav-link", "index": ALL}, "active"),
    Input("url", "pathname"),
    State({"type": "nav-link", "index": ALL}, "href"),
)
def update_active_links(pathname, hrefs):
    return [pathname == href for href in hrefs]

if __name__ == "__main__":
    app.run(debug=True)

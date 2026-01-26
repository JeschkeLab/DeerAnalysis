import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback
from deeranalysis.utils.database import init_db
from dash_iconify import DashIconify
import dash_mantine_components as dmc

# Initialize database
init_db()

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dmc.styles.ALL])
server = app.server

def get_icon(icon):
    return DashIconify(icon=icon, width=20)

def create_nav_link(label, href, icon):
    return dmc.NavLink(
        label=label,
        href=href,
        leftSection=get_icon(icon) if icon else None,
        id={"type": "nav-link", "index": href},
        h=32,
    )

sidebar_content = dmc.Stack(
    [
        dmc.Text("Datasets", size="sm", c="dimmed", fw=500),
        create_nav_link("File Upload", "/upload", "mdi:upload"),
        create_nav_link("Logs Upload", "/logs_upload", "mdi:file-document-outline"),
        create_nav_link("Datasets", "/", "mdi:database"),
        create_nav_link("Comparison", "/comparison", "mdi:compare"),
        
        dmc.Divider(my="sm"),
        
        dmc.Text("DeerLab Fitting", size="sm", c="dimmed", fw=500),

        create_nav_link("autoDEER Fit", "/autoDEER", "mdi:auto-fix"),
        create_nav_link("Non-Parametric Fit", "/nonparametric", "mdi:chart-bell-curve-cumulative"),
        create_nav_link("Parametric Fit", "/parametric", "mdi:function-variant"),
        
        dmc.Divider(my="sm"),
        
        dmc.Text("DeerNet Fitting", size="sm", c="dimmed", fw=500),
        create_nav_link("DeerNet Fit", "/deernet", "mdi:brain"),
        
        dmc.Divider(my="sm"),

        dmc.Text("About", size="sm", c="dimmed", fw=500),
        create_nav_link("About DeerAnalysis", "/about", "mdi:information"),
        create_nav_link("Citation", "/citation", "mdi:format-quote-close"),
        dmc.NavLink(
            label="Github",
            href="https://github.com/JeschkeLab",
            leftSection=get_icon("mdi:github"),
            target="_blank",
            rightSection=get_icon("mdi:open-in-new"),
        ),

        dmc.Space(style={"flex": 1}),
        dmc.Group(
            [
                # dmc.ActionIcon(get_icon("mdi:cog"), variant="subtle", size="lg", component="a", href="/config"),
                # dmc.ActionIcon(get_icon("mdi:monitor"), variant="subtle", size="lg", component="a", href="/system_monitor"),
                create_nav_link("", "/config", "mdi:cog"),
                create_nav_link("", "/system_monitor", "mdi:monitor")
            ],
            mt="auto"
        )
    ],
    h="100%",
    gap=5,
    justify="space-between"
)

app.layout = dmc.MantineProvider(
    [
        dcc.Location(id="url"),
        dmc.AppShell(
            [
                dmc.AppShellHeader(
                    dmc.Group(
                        [
                            dmc.Burger(id="burger", hiddenFrom="sm", size="sm"),
                            dmc.Title("DeerAnalysis", order=3),
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
                        "© 2026 DeerAnalysis. Developed by Hugo Karas, Stefan Stoll and Gunnar Jeschke. All rights reserved.",
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
    ]
)

@callback(
    Output("app-shell", "navbar"),
    Input("burger", "opened"),
    State("app-shell", "navbar"),
)
def toggle_navbar(opened, navbar):
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

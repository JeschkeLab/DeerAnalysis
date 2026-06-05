import dash_mantine_components as dmc
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback
from dash_iconify import DashIconify
import os
import json
from pathlib import Path
from deeranalysis.utils.database import init_db, get_session, Settings, save_appearance_settings
_CONFIG_FILE = Path.home() / ".deeranalysis" / "config.json"
from importlib.metadata import version as get_version

def default_directory():
    """
    Finds the OS specific default directory at ~/DeerAnalysis.
    """
    home = os.path.expanduser("~")
    default_dir = os.path.join(home, "DeerAnalysis")
    return default_dir


def store_DeerAnalysis_directory(directory):
    """
    Persists the chosen directory path and creates the directory if needed.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w") as f:
        json.dump({"directory": str(directory)}, f)


def get_DeerAnalysis_directory():
    """
    Retrieves the stored DeerAnalysis directory.
    Falls back to the default directory if no config has been saved yet.
    """
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE) as f:
                data = json.load(f)
            stored = data.get("directory")
            if stored:
                return stored
        except (json.JSONDecodeError, KeyError):
            pass
    return default_directory()

def download_deernet_models():
    """
    Downloads the DeerNet models and stores them in the [DeerAnalysis directory]/deernet.
    """

    # mkdir deernet directory
    deernet_dir = os.path.join(get_DeerAnalysis_directory(), "deernet")
    if not os.path.exists(deernet_dir):
        os.makedirs(deernet_dir)
    
    # OG Hugo's polybox link (expires after 30.06.2024):
    # URL = r"https://polybox.ethz.ch/index.php/s/xbB5Yj6bT3PQNK4/download"
    # Latest github release attachment
    try:
        _version = get_version("DeerAnalysis")
    except Exception as e:
        print(f"Could not get DeerAnalysis version: {e}")
        _version = "latest"

    URL_version = rf"https://github.com/JeschkeLab/DeerAnalysis/releases/download/v{_version}/deernet_models.zip"
    URL_latest = r"https://github.com/JeschkeLab/DeerAnalysis/releases/latest/download/deernet_models.zip"

    # download the file and save it to the deernet directory
    import requests
    response = requests.get(URL_version)
    if response.status_code != 200:
        response = requests.get(URL_latest)
    if response.status_code == 200:
        with open(os.path.join(deernet_dir, "deernet_models.zip"), "wb") as f:
            f.write(response.content)
        # unzip the file
        import zipfile
        with zipfile.ZipFile(os.path.join(deernet_dir, "deernet_models.zip"), "r") as zip_ref:
            zip_ref.extractall(deernet_dir)
        # remove the zip file
        os.remove(os.path.join(deernet_dir, "deernet_models.zip"))
    else:
        print("Failed to download DeerNet models. Please try again later.")

def set_logs_api_key(URL, api_key):
    session = get_session()
    settings = session.query(Settings).first()
    if not settings:
        settings = Settings()
    settings.logs_url = URL
    settings.logs_api_key = api_key
    session.add(settings)
    session.commit()



def create_setup_modal(id="setup-modal"):
    n_steps = 4

    @callback(
        Output(f"{id}-stepper", "active",allow_duplicate=True),
        Output(id, "opened",allow_duplicate=True),
        Output("color-scheme-store", "data", allow_duplicate=True),
        Output("ui-scale-store", "data", allow_duplicate=True),
        Input("next-basic-usage", "n_clicks"),
        State(f"{id}-stepper", "active"),
        State(f"{id}-database-path","value"),
        State(f"{id}-color-scheme", "checked"),
        State(f"{id}-ui-scale", "value"),
        prevent_initial_call=True
    )
    def next_step(n_clicks, active, directory, dark_mode, ui_scale):
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        if active == 0:
            # Store the directory and create it if it does not exist
            store_DeerAnalysis_directory(directory)
            init_db(directory)
        if active == 2:
            # Store the logs API key and URL
            logs_url = dash.callback_context.states.get(f"{id}-logs-server-url.value", "")
            logs_api_key = dash.callback_context.states.get(f"{id}-logs-api-key.value", "")
            if logs_url and logs_api_key:
                set_logs_api_key(logs_url, logs_api_key)

        if active < n_steps - 1:
            return active + 1, dash.no_update, dash.no_update, dash.no_update
        elif active == n_steps - 1:
            # Save appearance settings and close the modal
            color_scheme = "dark" if dark_mode else "light"
            scale = ui_scale if ui_scale is not None else 1.0
            save_appearance_settings(color_scheme, scale)
            return active, False, color_scheme, scale

        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        

    
    @callback(
        Output(f"{id}-stepper", "active",allow_duplicate=True),
        Input("back-basic-usage", "n_clicks"),
        State(f"{id}-stepper", "active"),
        prevent_initial_call=True
    )
    def previous_step(n_clicks, active):
        if not n_clicks:
            return dash.no_update
        if active == 0:
            return active
        return active - 1 
    
    @callback(
        Output("download-deernet-models", "leftSection"),
        Output("download-deernet-models", "variant"),
        Output("download-deernet-models", "loading"),
        Input("download-deernet-models", "n_clicks"),
        prevent_initial_call=True
    )
    def download_models(n_clicks):
        if n_clicks:
            download_deernet_models()
            return DashIconify(icon="tabler:check", color="green"), "filled", False
        return dash.no_update


    layout = dmc.Modal(id=id,
                       size="60%",
                       title="Welcome to DeerAnalysis 2026!",
                       children=[
        dmc.Stepper(
            id=f"{id}-stepper",
            active=0,
            allowNextStepsSelect=False,
            children=[
                dmc.StepperStep(
                    label="Step 1:",
                    description="Create the database",
                    children=[
                        html.P("To use DeerAnalysis, you first need to create a local database. This database will store metadata about your datasets, fits, and analysis results."),
                        dmc.TextInput(
                            id=f"{id}-database-path",
                            label="Database Path",
                            placeholder=default_directory(),
                            value=default_directory(),
                            className="mb-3"
                        ),
                        html.P("The folder and database will be created when you click next-step.")
                    ]
                ),
                dmc.StepperStep(
                    label="Step 2:",
                    description="DeerNet",
                    children=[
                        dmc.Text("DeerNet is neural network based tool for analysing DEER data."),
                        dmc.Text("DeerNet is an optional plugin for DeerAnalysis, but requires the AI-models to be downloaded. If you want to use DeerNet, please download the models using the green button below. This can also be done later in the settings page."),
                        dmc.Button("Download DeerNet Models", id="download-deernet-models", variant="outline", color="green", className="mt-2"),
                    ]
                ),
                dmc.StepperStep(
                    label="Step 3:",
                    description=dmc.Group([dmc.Text("LOGS Plugin (optional)", size="sm"), dmc.Badge("Beta", color="orange", variant="light", size="sm")], gap="xs"),
                    children=[
                        dmc.Text("For users of the LOGS data-repository from SciY (Bruker), we have implemented a plugin to import data directly"),
                        dmc.Text("To use the LOGS plugin, you need to have a API-key for your server, and the server needs to be running and accessible."),
                        dmc.Text("If you want to use the LOGS plugin, please enter your API key and server URL below. This can also be done later in the settings page."),
                        dmc.TextInput(id=f"{id}-logs-server-url", label="LOGS Server URL", placeholder="https://my-logs-server.com/groupname", className="mb-3"),
                        dmc.TextInput(id=f"{id}-logs-api-key", label="LOGS API Key", placeholder="my-api-key", className="mb-3"),
                    ]),
                dmc.StepperStep(
                    label="Step 4:",
                    description="Appearance",
                    children=[
                        dmc.Text("Customize the appearance of DeerAnalysis. These settings can be changed at any time in the configuration page."),
                        dmc.Stack([
                            dmc.Switch(
                                id=f"{id}-color-scheme",
                                label="Dark Mode",
                                description="Enable dark color scheme",
                                checked=False,
                                size="md",
                                mt="md",
                                onLabel=DashIconify(icon="tabler:moon", width=16),
                                offLabel=DashIconify(icon="tabler:sun", width=16),
                            ),
                            dmc.Stack([
                                dmc.Text("UI Scale", size="sm", fw=500, mt="md"),
                                dmc.Text("Adjust the size of all interface elements", size="xs", c="dimmed"),
                                dmc.Slider(
                                    id=f"{id}-ui-scale",
                                    value=1.0,
                                    min=0.75,
                                    max=1.5,
                                    step=0.05,
                                    marks=[
                                        {"value": 0.75, "label": "XS"},
                                        {"value": 1.0, "label": "Normal"},
                                        {"value": 1.25, "label": "Large"},
                                        {"value": 1.5, "label": "XL"},
                                    ],
                                    mt="xs",
                                    mb="xl",
                                ),
                            ], gap=0),
                        ], gap="xs"),
                    ]),
                    ]),
            dmc.Group(
                    justify="center",
                    mt="xl",
                    children=[
                        dmc.Button("Back", id="back-basic-usage", variant="default"),
                        dmc.Button("Next step", id="next-basic-usage"),
                    ],
                ),
        ])
    
    clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output("download-deernet-models", "loading", allow_duplicate=True),
        Input("download-deernet-models", "n_clicks"),
        prevent_initial_call=True,
    )
    return layout

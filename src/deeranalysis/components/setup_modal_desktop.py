import dash_mantine_components as dmc
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback
from dash_iconify import DashIconify
import os
from deeranalysis.utils.database import init_db, get_session,Settings

def default_directory():
    """
    Finds the OS specific default dirfectory at ~/DeerAnalysis.
    """
    home = os.path.expanduser("~")
    default_dir = os.path.join(home, "DeerAnalysis")
    return default_dir


def store_DeerAnalysis_directory(directory):
    """
    Stores and created the  directory
    """

    # Check if the directory exists, if not create it
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_DeerAnalysis_directory():
    """
    Retrieves the stored DeerAnalysis directory. If it does not exist, returns the default directory.
    """
    directory = default_directory()
    if not os.path.exists(directory):
        return default_directory()
    return directory

def download_deernet_models():
    """
    Downloads the DeerNet models and stores them in the [DeerAnalysis directory]/deernet.
    """

    # mkdir deernet directory
    deernet_dir = os.path.join(get_DeerAnalysis_directory(), "deernet")
    if not os.path.exists(deernet_dir):
        os.makedirs(deernet_dir)
    
    URL = r"https://polybox.ethz.ch/index.php/s/xbB5Yj6bT3PQNK4/download"

    # download the file and save it to the deernet directory
    import requests
    response = requests.get(URL)
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
    n_steps = 3

    @callback(
        Output(f"{id}-stepper", "active",allow_duplicate=True),
        Output(id, "opened",allow_duplicate=True),
        Input("next-basic-usage", "n_clicks"),
        State(f"{id}-stepper", "active"),
        State(f"{id}-database-path","value"),
        prevent_initial_call=True
    )
    def next_step(n_clicks, active,directory):
        if not n_clicks:
            return dash.no_update
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
            return active + 1, dash.no_update
        elif active == n_steps - 1:
            # Close the modal
            return active, False

        return dash.no_update
        

    
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
                       title="Welcome to DeerAnalysis!",
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
                        dmc.Text("DeerNet is an optional-plugin for DeerAnalysis, but requires the AI-models to be downloaded. If you want to use DeerNet, please download the models using the button below. This can also be done later in the settings page."),
                        dmc.Button("Download DeerNet Models", id="download-deernet-models", variant="outline", color="green", className="mt-2"),
                    ]
                ),
                dmc.StepperStep(
                    label="Step 3:",
                    description="LOGS Plugin (optional)",
                    children=[
                        dmc.Text("For users of the LOGS data-repository from SciY (Bruker), we have implemented a plugin to import data directly"),
                        dmc.Text("To use the LOGS plugin, you need to have a API-key for your server, and the server needs to be running and accessible."),
                        dmc.Text("If you want to use the LOGS plugin, please enter your API key and server URL below. This can also be done later in the settings page."),
                        dmc.TextInput(id=f"{id}-logs-server-url", label="LOGS Server URL", placeholder="https://my-logs-server.com/groupname", className="mb-3"),
                        dmc.TextInput(id=f"{id}-logs-api-key", label="LOGS API Key", placeholder="my-api-key", className="mb-3"),
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

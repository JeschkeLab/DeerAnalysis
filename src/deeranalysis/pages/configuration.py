import dash
from dash import html, dcc, callback, Input, Output, State, clientside_callback
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from importlib.metadata import version as get_version
import sys
from deeranalysis.utils.logs_plugin import get_logs_api_db, set_logs_api_key
from deeranalysis.utils.database import get_appearance_settings, save_appearance_settings
from deerlab import show_config
dash.register_page(__name__, path='/config')
page_id= 'config'


try:
    _current_version = get_version("DeerAnalysis")
except Exception:
    _current_version = "unknown"

try:
    _current_python_version = ".".join(map(str, sys.version_info[:3]))
except Exception:
    _current_python_version = "unknown"

try:
    _current_deerlab_version = get_version("deerlab")
except Exception:
    _current_deerlab_version = "unknown"



layout = dmc.Container([
    dmc.Title("Configuration", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    
    dmc.Accordion(
        multiple=True,
        value=["about","general"],
        children=[
            # About / Version
            dmc.AccordionItem(
                value="about",
                children=[
                    dmc.AccordionControl(
                        "About",
                        icon=DashIconify(icon="mdi:information-outline", width=20),
                    ),
                    dmc.AccordionPanel([
                        dmc.Stack([
                            dmc.Group([
                                dmc.Text("Installed version", size="sm", w=160, c="dimmed"),
                                dmc.Badge(_current_version, color="blue", variant="light"),
                            ], gap="xs"),
                            dmc.Group([
                                dmc.Text("Latest version", size="sm", w=160, c="dimmed"),
                                dmc.Badge(
                                    id="config-latest-version-badge",
                                    children="Checking...",
                                    color="gray",
                                    variant="light",
                                ),
                                dmc.Badge(
                                    id="config-version-status-badge",
                                    children="",
                                    variant="dot",
                                    style={"display": "none"},
                                ),
                            ], gap="xs"),
                            dmc.Group([
                                dmc.Text("Python version", size="sm", w=160, c="dimmed"),
                                dmc.Badge(_current_python_version, color="blue", variant="light"),
                            ], gap="xs"),
                            dmc.Group([
                                dmc.Text("DeerLab version", size="sm", w=160, c="dimmed"),
                                dmc.Badge(_current_deerlab_version, color="blue", variant="light"),
                            ], gap="xs"),
                        ], gap="sm"),
                    ]),
                ],
            ),

            # General Settings
            dmc.AccordionItem(
                value="general",
                children=[
                    dmc.AccordionControl(
                        "General Settings",
                        icon=DashIconify(icon="mdi:cog", width=20)
                    ),
                    dmc.AccordionPanel([
                        dmc.Stack([
                            dmc.Switch(
                                id="config-dark-mode",
                                label="Dark Mode",
                                description="Enable dark mode theme",
                                size="md",
                                mb="sm",
                                onLabel=DashIconify(icon="tabler:moon", width=16),
                                offLabel=DashIconify(icon="tabler:sun", width=16),
                            ),
                            dmc.Stack([
                                dmc.Text("UI Scale", size="sm", fw=500),
                                dmc.Text("Adjust the size of all interface elements", size="xs", c="dimmed"),
                                dmc.Slider(
                                    id="config-ui-scale",
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
                            ], gap=0, mb="sm"),
                            # dmc.Switch(
                            #     id="config-auto-save",
                            #     label="Auto-save Results",
                            #     description="Automatically save fit results to database",
                            #     checked=True,
                            #     size="md",
                            #     mb="sm"
                            # ),
                            # dmc.NumberInput(
                            #     id="config-max-datasets",
                            #     label="Maximum Displayed Datasets",
                            #     description="Maximum number of datasets to display in tables",
                            #     value=100,
                            #     min=10,
                            #     max=1000,
                            #     step=10,
                            #     mb="sm"
                            # ),
                            # dmc.TextInput(
                            #     id="config-default-path",
                            #     label="Data Directory",
                            #     description="The directory for loading data files",
                            #     placeholder="/path/to/data",
                            #     mb="sm"
                            # ),
                            dmc.Select(
                                id="config-plot-theme",
                                label="Plot Theme",
                                description="Default theme for plotly figures (Auto follows dark/light mode)",
                                data=[
                                    {"value": "auto", "label": "Auto (follows dark mode)"},
                                    {"value": "plotly", "label": "Plotly"},
                                    {"value": "plotly_white", "label": "Plotly White"},
                                    {"value": "plotly_dark", "label": "Plotly Dark"},
                                    {"value": "ggplot2", "label": "ggplot2"},
                                    {"value": "seaborn", "label": "Seaborn"},
                                ],
                                value="auto",
                                mb="sm"
                            ),
                            dmc.Button(
                                id='db-reset-btn',
                                color='red',
                                variant='outline',
                                leftSection=DashIconify(icon="mdi:database-remove", width=20),
                                children="Reset Database",
                                mt="md"
                            ),
                            dmc.Modal(
                                id="db-reset-modal",
                                title="Confirm Database Reset",
                                centered=True,
                                children=[
                                    html.P("Are you sure you want to reset the database? This will delete all stored datasets, fits, and results. This action cannot be undone."),
                                    dmc.Group([
                                        dmc.Button("Cancel", id="db-reset-cancel-btn", color="gray", variant="outline"),
                                        dmc.Button("Confirm Reset", id="db-reset-confirm-btn", color="red")
                                    ], justify="flex-end", mt="md")
                                ]
                            )
                        ])
                    ])
                ]
            ),
            
            # # DeerLab Settings
            # dmc.AccordionItem(
            #     value="deerlab",
            #     children=[
            #         dmc.AccordionControl(
            #             "DeerLab Settings",
            #             icon=DashIconify(icon="mdi:chart-bell-curve", width=20)
            #         ),
            #         dmc.AccordionPanel([
            #             dmc.Stack([
            #                 dmc.NumberInput(
            #                     id="config-dl-max-iterations",
            #                     label="Maximum Iterations",
            #                     description="Maximum number of iterations for fitting algorithms",
            #                     value=10000,
            #                     min=100,
            #                     max=1000000,
            #                     step=1000,
            #                     mb="sm",
            #                     allowDecimal=False
            #                 ),
            #                 dmc.NumberInput(
            #                     id="config-dl-tolerance",
            #                     label="Convergence Tolerance",
            #                     description="Tolerance for convergence criteria",
            #                     value=1e-6,
            #                     min=1e-10,
            #                     max=1e-3,
            #                     step=1e-7,
            #                     decimalScale=10,
            #                     mb="sm"
            #                 ),
            #                 dmc.Select(
            #                     id="config-dl-regparam-method",
            #                     label="Default Regularization Parameter Method",
            #                     description="Method for selecting regularization parameter",
            #                     data=[
            #                         {"value": "aic", "label": "AIC (Akaike Information Criterion)"},
            #                         {"value": "bic", "label": "BIC (Bayesian Information Criterion)"},
            #                         {"value": "cv", "label": "Cross-Validation"},
            #                         {"value": "gcv", "label": "Generalized Cross-Validation"},
            #                     ],
            #                     value="bic",
            #                     mb="sm"
            #                 ),
            #                 dmc.Select(
            #                     id='config-dl-nnls-backend',
            #                     label='Default NNLS Backend',
            #                     description='Default solver used to solve a non-negative least-squares problem',
            #                     data=[
            #                         {'value': 'qp', 'label': 'quadprog'},
            #                         {'value': 'cvx', 'label': 'cvxopt'},
            #                         {'value': 'fnnls', 'label': 'fast NNLS'},
            #                     ],
            #                     value='qp',
            #                     mb='sm'     
            #                 ),
            #                 dmc.NumberInput(
            #                     id="config-dl-bootstrap-samples",
            #                     label="Default Bootstrap Samples",
            #                     description="Number of bootstrap samples for uncertainty analysis",
            #                     value=50,
            #                     min=10,
            #                     max=1000,
            #                     step=10,
            #                     allowDecimal=False,
            #                     mb="sm"
            #                 ),
            #             ])
            #         ])
            #     ]
            # ),
            
            # DeerNet Settings
            dmc.AccordionItem(
                value="deernet",
                children=[
                    dmc.AccordionControl(
                        "DeerNet Settings",
                        icon=DashIconify(icon="mdi:brain", width=20)
                    ),
                    dmc.AccordionPanel([
                        dmc.Stack([
                            dmc.Button(
                                "Download/Re-Download Models",
                                id = 'dn-model-download',
                                 variant="outline"
                            ),
                            dmc.Select(
                                id="config-dn-default-model-size",
                                label="Default Model Size",
                                description="Default neural network model size",
                                data=[
                                    {"value": "128", "label": "128"},
                                    {"value": "256", "label": "256"},
                                    {"value": "512", "label": "512"},
                                ],
                                value="512",
                                mb="sm"
                            ),
                            # dmc.Select(
                            #     id="config-dn-uncertainty-type",
                            #     label="Default Uncertainty Type",
                            #     description="Default method for uncertainty quantification",
                            #     data=[
                            #         {"value": "net", "label": "Network Ensemble"},
                            #         {"value": "boot", "label": "Bootstrap"},
                            #     ],
                            #     value="net",
                            #     mb="sm"
                            # ),
                            # dmc.NumberInput(
                            #     id="config-dn-ensemble-size",
                            #     label="Ensemble Size",
                            #     description="Number of networks in ensemble for uncertainty",
                            #     value=10,
                            #     min=5,
                            #     max=50,
                            #     step=5,
                            #     mb="sm"
                            # ),
                            # dmc.Switch(
                            #     id="config-dn-gpu-acceleration",
                            #     label="GPU Acceleration",
                            #     description="Use GPU for DeerNet inference (if available)",
                            #     checked=False,
                            #     size="md",
                            #     mb="sm"
                            # ),
                            # dmc.TextInput(
                            #     id="config-dn-model-path",
                            #     label="Custom Model Path",
                            #     description="Path to custom DeerNet models (optional)",
                            #     placeholder="/path/to/models",
                            #     mb="sm"
                            # ),
                        ])
                    ])
                ]
            ),
            
            # LogsPlugin Settings
            dmc.AccordionItem(
                value="logsplugin",
                children=[
                    dmc.AccordionControl(
                        "LogsPlugin Settings",
                        icon=DashIconify(icon="mdi:file-document-outline", width=20)
                    ),
                    dmc.AccordionPanel([
                        dmc.Stack([
                            dmc.TextInput(
                                id="config-logs-api-url",
                                label="Logs API URL",
                                description="URL for the logs API endpoint",
                                placeholder="https://api.example.com/logs",
                                mb="sm"
                            ),
                            dmc.PasswordInput(
                                id="config-logs-api-key",
                                label="Logs API Key",
                                description="API key for authentication",
                                placeholder="Enter your API key",
                                mb="sm"
                            ),
                        ])
                    ])
                ]
            ),
        ],
    ),
    
    dmc.Space(h="xl"),
    
    dmc.Group([
        dmc.Button(
            "Save Configuration",
            id="config-save-btn",
            leftSection=DashIconify(icon="mdi:content-save", width=20),
            color="blue",
        ),
        dmc.Button(
            "Reset to Defaults",
            id="config-reset-btn",
            leftSection=DashIconify(icon="mdi:restore", width=20),
            variant="outline",
            color="gray",
        ),
    ]),
    
    dmc.Space(h="md"),

    dmc.Modal(
        id="config-reset-modal",
        title="Confirm Reset",
        centered=True,
        children=[
            html.P("Are you sure you want to reset all settings to their default values? This action cannot be undone."),
            dmc.Group([
                dmc.Button("Cancel", id="config-reset-cancel-btn", color="gray", variant="outline"),
                dmc.Button("Confirm Reset", id="config-reset-confirm-btn", color="red")
            ], justify="flex-end", mt="md")
        ]
    ),
    
    dmc.Notification(
        id="config-notification",
        title="",
        message="",
        action="hide",
    ),
    
], size="lg", py="md")

clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output("dn-model-download", "loading", allow_duplicate=True),
        Input("dn-model-download", "n_clicks"),
        prevent_initial_call=True,
    )


# Callbacks for saving and resetting configuration
@callback(
    Output("config-notification", "action"),
    Output("config-notification", "title"),
    Output("config-notification", "message"),
    Output("config-notification", "color"),
    Output("color-scheme-store", "data", allow_duplicate=True),
    Output("ui-scale-store", "data", allow_duplicate=True),
    Output("plot-theme-store", "data", allow_duplicate=True),
    Input("config-save-btn", "n_clicks"),
    State("config-dark-mode", "checked"),
    State("config-ui-scale", "value"),
    # State("config-default-path", "value"),
    State("config-plot-theme", "value"),
    State("config-logs-api-url", "value"),
    State("config-logs-api-key", "value"),
    prevent_initial_call=True
)
def save_configuration(n_clicks, dark_mode, ui_scale, plot_theme, logs_url, logs_api_key):
    if n_clicks:
        try:
            if logs_url and logs_api_key:
                set_logs_api_key(logs_url, logs_api_key)
            color_scheme = "dark" if dark_mode else "light"
            scale = ui_scale if ui_scale is not None else 1.0
            theme = plot_theme or "auto"
            save_appearance_settings(color_scheme, scale, theme)
            return "show", "Success", "Configuration saved successfully", "green", color_scheme, scale, theme
        except Exception as e:
            return "show", "Error", f"Failed to save configuration: {str(e)}", "red", dash.no_update, dash.no_update, dash.no_update
    return "hide", "", "", "blue", dash.no_update, dash.no_update, dash.no_update


@callback(
    Output("config-dark-mode", "checked"),
    Output("config-ui-scale", "value"),
    Output("config-plot-theme", "value"),
    Input("config-dark-mode", "id"),
)
def load_appearance_on_page_load(_):
    color_scheme, scale, plot_theme = get_appearance_settings()
    return color_scheme == "dark", scale, plot_theme or "auto"


@callback(
    Output("config-reset-modal", "opened", allow_duplicate=True),
    Input("config-reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_configuration(n_clicks):
    if (n_clicks):
        # This callback now just triggers the modal
        return True if n_clicks else False
    return False


# Trigger callback on page load and after save to keep values updated
@callback(
    Output("config-logs-api-url", "value"),
    Output("config-logs-api-key", "value"),
    Input("config-logs-api-url", "id"),
    Input("config-notification", "action"),  # Refresh after save
    prevent_initial_call=False
)
def load_logs_values_on_page_load(_, notification_action):
    """Load LOGS API credentials from database"""
    url, apiKey = get_logs_api_db()
    return url or "", apiKey or ""

###############################################################################
# Callbacks for downloading DeerNet model
###############################################################################
@callback(
        Output("dn-model-download", "leftSection"),
        Output("dn-model-download", "variant"),
        Output("dn-model-download", "loading"),
        Input("dn-model-download","n_clicks"),
        prevent_initial_call=True
)
def download_deernet_models(n_clicks):
    from deeranalysis.components.setup_modal_desktop import download_deernet_models
    if n_clicks:
        download_deernet_models()
        return DashIconify(icon="tabler:check", color="green"), "filled", False
    return dash.no_update


###############################################################################
# Callbacks for handling database reset confirmation
###############################################################################

@callback(
    Output("config-reset-modal", "opened", allow_duplicate=True),
    Input("config-reset-cancel-btn", "n_clicks"),
    Input("config-reset-confirm-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_reset_modal(n_clicks_cancel, n_clicks_confirm):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == "config-reset-confirm-btn" and n_clicks_confirm:
        # Here you would reset the configuration to defaults
        # For now, just show a success notification
        return False  # Close the modal after confirming reset
    elif button_id == "config-reset-cancel-btn" and n_clicks_cancel:
        return False  # Close the modal if cancel is clicked
    
    return dash.no_update  # Do not change modal state for other cases


@callback(
    Output("db-reset-modal", "opened", allow_duplicate=True),
    Input("db-reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_db(n_clicks):
    if n_clicks:
        return True
    return False

@callback(
    Output("config-latest-version-badge", "children"),
    Output("config-latest-version-badge", "color"),
    Output("config-version-status-badge", "children"),
    Output("config-version-status-badge", "color"),
    Output("config-version-status-badge", "style"),
    Input("version-check-store", "data"),
)
def _update_version_badges(data):
    if not data:
        return "Checking...", "gray", "", "gray", {"display": "none"}
    if data.get("error"):
        return "Unavailable", "red", "Check failed", "red", {"display": "inline-flex"}
    latest = data.get("latest_version", "unknown")
    if data.get("update_available"):
        return latest, "green", "Update available", "green", {"display": "inline-flex"}
    return latest, "blue", "Up to date", "teal", {"display": "inline-flex"}


@callback(
    Output("db-reset-modal", "opened", allow_duplicate=True),
    Input("db-reset-cancel-btn", "n_clicks"),
    Input("db-reset-confirm-btn", "n_clicks"),
    prevent_initial_call=True
)
def close_db_reset_modal(n_clicks_cancel, n_clicks_confirm):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == "db-reset-confirm-btn" and n_clicks_confirm:
        from deeranalysis.utils.database import reset_db
        reset_db()
        return False  # Close the modal after confirming reset
    elif button_id == "db-reset-cancel-btn" and n_clicks_cancel:
        return False  # Close the modal if cancel is clicked
    
    return dash.no_update  # Do not change modal state for other cases


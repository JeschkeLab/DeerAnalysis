import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash_iconify import DashIconify

dash.register_page(__name__, path='/config')


layout = dmc.Container([
    dmc.Title("Configuration", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    
    dmc.Accordion(
        multiple=True,
        value=["general"],
        children=[
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
                                mb="sm"
                            ),
                            dmc.Switch(
                                id="config-auto-save",
                                label="Auto-save Results",
                                description="Automatically save fit results to database",
                                checked=True,
                                size="md",
                                mb="sm"
                            ),
                            dmc.NumberInput(
                                id="config-max-datasets",
                                label="Maximum Displayed Datasets",
                                description="Maximum number of datasets to display in tables",
                                value=100,
                                min=10,
                                max=1000,
                                step=10,
                                mb="sm"
                            ),
                            dmc.TextInput(
                                id="config-default-path",
                                label="Default Data Path",
                                description="Default directory for loading data files",
                                placeholder="/path/to/data",
                                mb="sm"
                            ),
                            dmc.Select(
                                id="config-plot-theme",
                                label="Plot Theme",
                                description="Default theme for plotly figures",
                                data=[
                                    {"value": "plotly", "label": "Plotly"},
                                    {"value": "plotly_white", "label": "Plotly White"},
                                    {"value": "plotly_dark", "label": "Plotly Dark"},
                                    {"value": "ggplot2", "label": "ggplot2"},
                                    {"value": "seaborn", "label": "Seaborn"},
                                ],
                                value="plotly_white",
                                mb="sm"
                            ),
                        ])
                    ])
                ]
            ),
            
            # DeerLab Settings
            dmc.AccordionItem(
                value="deerlab",
                children=[
                    dmc.AccordionControl(
                        "DeerLab Settings",
                        icon=DashIconify(icon="mdi:chart-bell-curve", width=20)
                    ),
                    dmc.AccordionPanel([
                        dmc.Stack([
                            dmc.NumberInput(
                                id="config-dl-max-iterations",
                                label="Maximum Iterations",
                                description="Maximum number of iterations for fitting algorithms",
                                value=10000,
                                min=100,
                                max=1000000,
                                step=1000,
                                mb="sm",
                                allowDecimal=False
                            ),
                            dmc.NumberInput(
                                id="config-dl-tolerance",
                                label="Convergence Tolerance",
                                description="Tolerance for convergence criteria",
                                value=1e-6,
                                min=1e-10,
                                max=1e-3,
                                step=1e-7,
                                decimalScale=10,
                                mb="sm"
                            ),
                            dmc.Select(
                                id="config-dl-regparam-method",
                                label="Default Regularization Parameter Method",
                                description="Method for selecting regularization parameter",
                                data=[
                                    {"value": "aic", "label": "AIC (Akaike Information Criterion)"},
                                    {"value": "bic", "label": "BIC (Bayesian Information Criterion)"},
                                    {"value": "cv", "label": "Cross-Validation"},
                                    {"value": "gcv", "label": "Generalized Cross-Validation"},
                                ],
                                value="bic",
                                mb="sm"
                            ),
                            dmc.Select(
                                id='config-dl-nnls-backend',
                                label='Default NNLS Backend',
                                description='Default solver used to solve a non-negative least-squares problem',
                                data=[
                                    {'value': 'qp', 'label': 'quadprog'},
                                    {'value': 'cvx', 'label': 'cvxopt'},
                                    {'value': 'fnnls', 'label': 'fast NNLS'},
                                ],
                                value='qp',
                                mb='sm'     
                            ),
                            dmc.NumberInput(
                                id="config-dl-bootstrap-samples",
                                label="Default Bootstrap Samples",
                                description="Number of bootstrap samples for uncertainty analysis",
                                value=50,
                                min=10,
                                max=1000,
                                step=10,
                                allowDecimal=False,
                                mb="sm"
                            ),
                            dmc.Switch(
                                id="config-dl-phase-correction",
                                label="Automatic Phase Correction",
                                description="Apply automatic phase correction to data",
                                checked=True,
                                size="md",
                                mb="sm"
                            ),
                            dmc.Switch(
                                id="config-dl-zero-time-correction",
                                label="Automatic Zero-Time Correction",
                                description="Apply automatic zero-time correction",
                                checked=True,
                                size="md",
                                mb="sm"
                            ),
                        ])
                    ])
                ]
            ),
            
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
                            dmc.Select(
                                id="config-dn-uncertainty-type",
                                label="Default Uncertainty Type",
                                description="Default method for uncertainty quantification",
                                data=[
                                    {"value": "net", "label": "Network Ensemble"},
                                    {"value": "boot", "label": "Bootstrap"},
                                ],
                                value="net",
                                mb="sm"
                            ),
                            dmc.NumberInput(
                                id="config-dn-ensemble-size",
                                label="Ensemble Size",
                                description="Number of networks in ensemble for uncertainty",
                                value=10,
                                min=5,
                                max=50,
                                step=5,
                                mb="sm"
                            ),
                            dmc.Switch(
                                id="config-dn-gpu-acceleration",
                                label="GPU Acceleration",
                                description="Use GPU for DeerNet inference (if available)",
                                checked=False,
                                size="md",
                                mb="sm"
                            ),
                            dmc.TextInput(
                                id="config-dn-model-path",
                                label="Custom Model Path",
                                description="Path to custom DeerNet models (optional)",
                                placeholder="/path/to/models",
                                mb="sm"
                            ),
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


# Callbacks for saving and resetting configuration
@callback(
    Output("config-notification", "action"),
    Output("config-notification", "title"),
    Output("config-notification", "message"),
    Output("config-notification", "color"),
    Input("config-save-btn", "n_clicks"),
    State("config-dark-mode", "checked"),
    State("config-auto-save", "checked"),
    State("config-max-datasets", "value"),
    State("config-default-path", "value"),
    State("config-plot-theme", "value"),
    prevent_initial_call=True
)
def save_configuration(n_clicks, dark_mode, auto_save, max_datasets, default_path, plot_theme):
    if n_clicks:
        # Here you would save the configuration to a file or database
        # For now, just show a success notification
        return "show", "Success", "Configuration saved successfully", "green"
    return "hide", "", "", "blue"


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

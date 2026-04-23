import dash_mantine_components as dmc
import dash
from dash import html, dcc, callback, Input, Output, State
from dash_iconify import DashIconify


def check_github_release_version():
    import requests
    from packaging import version
    from importlib.metadata import version as get_version

    try:
        response = requests.get(
            "https://api.github.com/repos/JeschkeLab/DeerAnalysis/releases/latest",
            timeout=5,
        )
        response.raise_for_status()
        latest_release = response.json()

        if "tag_name" not in latest_release:
            return {"update_available": False, "error": "No releases found on GitHub."}

        latest_version = latest_release["tag_name"].lower().lstrip("v")
        current_version = get_version("DeerAnalysis")
        release_notes = latest_release.get("body", "")
        release_url = latest_release.get("html_url", "")

        update_available = version.parse(latest_version) > version.parse(current_version)

        return {
            "update_available": update_available,
            "current_version": current_version,
            "latest_version": latest_version,
            "release_notes": release_notes,
            "release_url": release_url,
            "error": None,
        }
    except Exception as e:
        return {"update_available": False, "error": str(e)}


def new_version_modal():
    """
    Checks if a new version of DeerAnalysis is available and displays a modal if so.
    The modal includes the new version number, release notes, and a link to the GitHub
    releases page.
    """
    return html.Div([
        dcc.Store(id="version-check-store", data=None),
        dcc.Interval(id="version-check-interval", interval=2000, max_intervals=1),
        dmc.Modal(
            id="new-version-modal",
            title=dmc.Group([
                DashIconify(icon="mdi:arrow-up-circle-outline", width=24, color="green"),
                dmc.Text("New Version Available", fw=600, size="lg"),
            ], gap="xs"),
            size="50%",
            opened=False,
            children=[
                dmc.Stack([
                    dmc.Alert(
                        id="new-version-alert",
                        children="",
                        color="green",
                        variant="light",
                        icon=DashIconify(icon="mdi:information-outline", width=18),
                    ),
                    dmc.Text("Release Notes", fw=500, size="sm"),
                    dmc.ScrollArea(
                        dcc.Markdown(
                            id="new-version-release-notes",
                            children="",
                            style={"fontSize": "13px"},
                        ),
                        h=200,
                        type="auto",
                        style={"border": "1px solid var(--mantine-color-default-border)", "borderRadius": "var(--mantine-radius-sm)", "padding": "8px"},
                    ),
                    dmc.Group([
                        dmc.Button(
                            "Close",
                            id="new-version-close-btn",
                            variant="subtle",
                            color="gray",
                        ),
                        html.A(
                            dmc.Button(
                                "View on GitHub",
                                leftSection=DashIconify(icon="mdi:github", width=16),
                                color="green",
                            ),
                            id="new-version-github-link",
                            href="#",
                            target="_blank",
                            style={"textDecoration": "none"},
                        ),
                    ], justify="flex-end", mt="xs"),
                ], gap="sm"),
            ],
        ),
    ])


def update_button():
    """
    Button for the header bar that appears when a newer version of DeerAnalysis is
    available. Size scales automatically with the UI Scale setting via the Mantine theme.
    """
    return dmc.ActionIcon(
        DashIconify(icon="mdi:arrow-up-circle-outline", width=20),
        id="update-available-btn",
        color="green",
        variant="subtle",
        size="lg",
        style={"display": "none"},
    )


# --- Callbacks ---

@callback(
    Output("version-check-store", "data"),
    Input("version-check-interval", "n_intervals"),
    prevent_initial_call=True,
)
def _run_version_check(_):
    return check_github_release_version()


@callback(
    Output("update-available-btn", "style"),
    Output("new-version-alert", "children"),
    Output("new-version-release-notes", "children"),
    Output("new-version-github-link", "href"),
    Input("version-check-store", "data"),
    prevent_initial_call=True,
)
def _update_version_ui(data):
    hidden = {"display": "none"}
    visible = {"display": "block"}

    if not data or not data.get("update_available"):
        return hidden, "", "", "#"

    current = data.get("current_version", "unknown")
    latest = data.get("latest_version", "unknown")
    notes = data.get("release_notes", "No release notes provided.")
    url = data.get("release_url", "#")

    alert_text = f"Version {latest} is available. You are currently running {current}."
    return visible, alert_text, notes, url


@callback(
    Output("new-version-modal", "opened"),
    Input("update-available-btn", "n_clicks"),
    Input("new-version-close-btn", "n_clicks"),
    State("new-version-modal", "opened"),
    prevent_initial_call=True,
)
def _toggle_new_version_modal(_open_clicks, _close_clicks, is_open):
    trigger = dash.ctx.triggered_id
    if trigger == "update-available-btn":
        return True
    if trigger == "new-version-close-btn":
        return False
    return is_open

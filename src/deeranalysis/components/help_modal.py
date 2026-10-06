from functools import lru_cache
from pathlib import Path
import dash
from dash import dcc, callback, Input, Output, ALL, ctx, no_update
import dash_mantine_components as dmc
from dash_iconify import DashIconify

HELP_DIR = Path(__file__).parent.parent / "assets" / "help"

STYLE = {}

@lru_cache
def load_help(topic: str) -> tuple[str, str]:
    text = (HELP_DIR / f"{topic}.md").read_text(encoding="utf-8")
    # Use the first "# Heading" line as the modal title
    first, _, rest = text.partition("\n")
    if first.startswith("# "):
        return first[2:].strip(), rest
    return topic.replace("_", " ").title(), text

def help_button(topic: str, **kwargs):
    return dmc.ActionIcon(
        DashIconify(icon="material-symbols:help-outline", width=20),
        id={"type": "help-btn", "topic": topic},
        size="lg", variant="default", style={'marginTop': kwargs.pop('marginTop','25px')}, **kwargs,
    )

def help_modal():
    return dmc.Modal(
        id="help-modal", size="80%", opened=False,
        children=dcc.Markdown(id="help-modal-content", mathjax=True,
                              link_target="_blank",
                              className="help-markdown",
                              style=STYLE),
    )

@callback(
    Output("help-modal", "opened"),
    Output("help-modal", "title"),
    Output("help-modal-content", "children"),
    Input({"type": "help-btn", "topic": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_help(n_clicks):
    if not ctx.triggered_id or not any(n_clicks):
        return no_update, no_update, no_update
    title, body = load_help(ctx.triggered_id["topic"])
    return True, title, body

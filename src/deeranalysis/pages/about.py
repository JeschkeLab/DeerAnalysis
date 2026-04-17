import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, no_update, MATCH, ALL, ctx
import dash


dash.register_page(__name__)
page_id='about'


layout = dmc.Container(
    style={"maxWidth": 960},
    children=[
        dmc.Title("About DeerAnalysis 2026", order=1, mb="md"),
        dmc.Text("DeerAnalysis 2026 represents the latest generation of the DeerAnalysis software, a comprehensive tool for analyzing and interpreting data from double electron-electron resonance (DEER) experiments."),
        dmc.Text("This new version "),

        dmc.Title("Key Features", order=2, mt="xl", mb="md"),
        dmc.List(
            [
                dmc.ListItem("User-friendly web interface for streamlined analysis workflows."),
                dmc.ListItem("Integration of state-of-the-art fitting algorithms for accurate distance distribution extraction."),
                dmc.ListItem("Support for a wide range of data formats and experimental setups."),
                dmc.ListItem("Advanced visualization tools for interpreting results and comparing datasets."),
                dmc.ListItem("Extensive documentation and tutorials to assist users at all levels."),
            ],
            withPadding=False,
                mb="md",
        ),

]
)
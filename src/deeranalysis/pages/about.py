import dash_mantine_components as dmc
from dash import html, dcc
import dash


dash.register_page(__name__)
page_id='about'


layout = dmc.Container(
    style={"maxWidth": 960},
    children=[
        dmc.Title("About DeerAnalysis 2026", order=1, mb="md"),
        dmc.Text(
            "DeerAnalysis 2026 is a major redesign and re-release of the popular dipolar-EPR data "
            "processing tool, DeerAnalysis. Originally released in 2004 as a MATLAB-based GUI for "
            "Tikhonov-regularisation based approaches for extracting distance distributions from "
            "Double-Electron-Electron-Resonance (DEER) data, DeerAnalysis has been continuously updated "
            "since then. In 2026, DeerAnalysis moved to a modern Python and JavaScript based software "
            "stack with a completely redesigned user interface.",
            mb="md",
        ),

        dmc.Title("Improvements over DeerAnalysis 2022", order=2, mt="xl", mb="md"),
        dmc.List(
            [
                dmc.ListItem("Regularisation and parametric fitting using the latest DeerLab 1.2."),
                dmc.ListItem("Dataset and fit management with high-quality comparison."),
                dmc.ListItem("Based on a modern software stack (Python and JavaScript)."),
                dmc.ListItem("Compiled support on all major operating systems."),
                dmc.ListItem("Multi-pathway support (via DeerLab)."),
                dmc.ListItem("Support for compactness criterion for non-parametric models (via DeerLab)."),
                dmc.ListItem("Support for global and population based fitting (via DeerLab)."),
                dmc.ListItem("Neural-network based fitting via DeerNet."),
            ],
            withPadding=False,
            mb="md",
        ),

        dmc.Title("Citing DeerAnalysis", order=2, mt="xl", mb="md"),
        dmc.Text("When you use DeerAnalysis in your work, please cite the following publications:", mb="sm"),
        dmc.Stack(
            [
                dmc.Paper(
                    p="md",
                    withBorder=True,
                    children=[
                        dmc.Text("DeerLab: a comprehensive software package for analyzing dipolar electron paramagnetic resonance spectroscopy data", fw=700),
                        dmc.Text("Luis Fábregas Ibáñez, Gunnar Jeschke, Stefan Stoll", c="dimmed"),
                        dmc.Text("Magn. Reson., 1, 209–224, 2020", c="dimmed"),
                        dmc.Anchor("doi.org/10.5194/mr-1-209-2020", href="https://doi.org/10.5194/mr-1-209-2020", target="_blank"),
                    ],
                ),
                dmc.Paper(
                    p="md",
                    withBorder=True,
                    children=[
                        dmc.Text("Deep neural network processing of DEER data", fw=700),
                        dmc.Text("Steven G. Worswick, James A. Spencer, Gunnar Jeschke, Ilya Kuprov", c="dimmed"),
                        dmc.Text("Science Advances, 2018", c="dimmed"),
                        dmc.Anchor("doi.org/10.1126/sciadv.aat5218", href="https://doi.org/10.1126/sciadv.aat5218", target="_blank"),
                    ],
                ),
            ],
            mb="md",
        ),

        dmc.Title("License", order=2, mt="xl", mb="md"),
        dmc.Text(
            "DeerAnalysis is licensed under the MIT License. "
            "Copyright © 2026 by the Jeschke Lab, ETH Zurich. All rights reserved."
        ),
    ]
)

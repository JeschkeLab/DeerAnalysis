import dash
from dash import html
import dash_mantine_components as dmc

dash.register_page(__name__)

layout = dmc.Center(
    h="80vh",
    children=dmc.Stack(
        align="center",
        gap="xs",
        children=[
            # dmc.Image(
            #     src="/assets/logo.png",
            #     w=120,
            #     mb="md",
            # ),
            dmc.Title(
                "404",
                order=1,
                style={"fontSize": "6rem", "color": "#c0392b", "lineHeight": 1},
            ),
            dmc.Title(
                "Page Not Found",
                order=2,
                c="dark",
            ),
            dmc.Text(
                "The page you are looking for does not exist, is yet to be implemented or has been moved.",
                c="dimmed",
                size="md",
                maw=400,
                ta="center",
            ),
            dmc.Anchor(
                dmc.Button(
                    "Go to Home",
                    color="dark",
                    size="md",
                    radius="md",
                    mt="md",
                ),
                href="/",
                underline=False,
            ),
        ],
    ),
)
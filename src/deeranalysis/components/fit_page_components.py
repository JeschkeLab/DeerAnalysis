import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_options import regparam_options,background_models
from dash import dcc,html

def fit_save_download_buttons(page_id):
    return dmc.Group([
            dmc.Button("Run Fit", id={"type":"run-fit-btn","page":page_id}, color="blue",variant='outline', className="mb-2 ms-1",leftSection=DashIconify(icon='material-symbols:play-arrow', width=20)),
            dmc.Button("Save Fit", id={"type":"save-fit-btn","page":page_id}, color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:save', width=20)),
            dmc.Button("Download", id={"type":"download-fit-btn","page":page_id}, color="green",variant='outline', className="mb-2 ms-1", disabled=True, leftSection=DashIconify(icon='material-symbols:download', width=20)),
        ],gap="xs",)


def adv_fit_options_regularisation(page_id):
    return dmc.Group([
        dmc.Select(
            label='Regularization Method',
            description="Method for the automatic selection of the optimal regularization parameter:",
            id={"type": "regparam-method", "page": page_id},
            data=regparam_options,
            value='bic',
            clearable=False,
            allowDeselect=False,
        ),
        dmc.NumberInput(
            label="Fixed Regularization Parameter (α):",
            id={"type": "fixed-alpha", "page": page_id},
            placeholder="Set a fixed regularization parameter (overrides automatic selection)",
            disabled=True,
        ),
    ],gap="xs",)

def adv_fit_options_parametric(page_id):
    return dmc.Group([
        dmc.NumberInput(label="Maximum Iterations:",
                        id={"type": "max-iter", "page": page_id},
                        value=1000,
                        step=1,
                        min=1,
                        className="mb-2"),
    ],gap="xs",)


# def distance_slider(page_id):
#     return dmc.Stack([dmc.Text("Distance Axis:", size="md", fw=500, mb=4),
#         dcc.RangeSlider(
#                 id= {"type": "distance-axis", "page": page_id},
#                 min=1.5,
#                 max=12,
#                 step=0.25,
#                 value=[1.75, 6],
#                 marks={i: f'{i}' for i in range(1, 13)},
#                 allowCross=False,
#                 allow_direct_input=True,
#                 className="dmc"
#             )],gap=2,)

def distance_slider(page_id):
    return dcc.RangeSlider(
                    id= {"type": "distance-axis", "page": page_id},
                    min=1.5,
                    max=12,
                    step=0.5,
                    value=[1.5, 6],
                    marks={i: f'{i}' for i in range(1, 13)},
                    allowCross=False,
                    allow_direct_input=True,
                    className="dmc"
            )
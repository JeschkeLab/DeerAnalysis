import json
import dash
from dash import html, dcc, callback, Input, Output, State,clientside_callback
import dash_bootstrap_components as dbc
import numpy as np
import deerlab as dl
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from autodeer import DEERanalysis
from deeranalysis.utils.database import get_session, Dataset, Fit
from deeranalysis.utils import  dataarray_from_database_entry
from deeranalysis.components.dataset_search_model import create_dataset_modal
from deeranalysis.utils.deerlab_options import regparam_options,background_models, plotly_goodness_of_fit, plotly_deerlab,dists_stats_to_list, fit_to_dict,name_dataset_from_dict
from deeranalysis.components.fit_page_components import fit_save_download_buttons,distance_slider,adv_fit_options_parametric

dash.register_page(__name__)

default_fit_results_code = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

startup_message = dmc.Alert("Multi-population fitting is designed for globally fitting multiple datasest of different samples where there is more than 1-population presenet and where the ratio of these populations changes.",title="Note!", color="blue",withCloseButton=True)

page_id='population'

parametric_models = [
    {'label': '1 Gaussian', 'value': 'dd_gauss'},
    # {'label': '1 3D Rice', 'value': 'dd_rice'},
]
layout = html.Div([
    dmc.Title("Multi-Population Global Fitting", order=1, mb="md"),
    dmc.Divider(mb="lg"),
    
    
    dbc.Row([
        dbc.Col([
            startup_message,
            create_dataset_modal(page_id=page_id),
            html.Div([
                dmc.Group([dmc.MultiSelect(id={'type': 'dataset-dropdown', 'page': page_id}, label="Select a dataset", description="Between 2 and 5 dataset should selected.")],style={'flex': '1 1 0',"flexGrow":1}),
                dmc.ActionIcon(DashIconify(icon='material-symbols:search', width=20),
                                id={'type': 'open-dataset-search-btn', 'page': page_id}, size="lg", variant="default", style={'marginTop': '25px'})
            ], style={'display': 'flex', 'flexDirection': 'row', 'alignItems': 'flex-end', 'gap': '8px'}),            
            dmc.Space(h=10),     
            dmc.Select(
                label='Background Model',
                id='pop-bg-model',
                data=background_models,
                value='bg_hom3d',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),     
            dmc.CheckboxGroup(
                id='pop-pathways-options',
                label="Pathways to include:",
                description="These pathways will be applied to all datasets, if they are fesiable for the coresponding experiment.",
                children=dmc.Group([
                    dmc.Checkbox(value='1', label='1'),
                    dmc.Checkbox(value='2', label='2'),
                    dmc.Checkbox(value='3', label='3'),
                    dmc.Checkbox(value='4', label='4'),
                    dmc.Checkbox(value='5', label='5'),
                ]),
                value=['1'], # Default selected pathways
            ),
            # Small vertical space
            dmc.Space(h=10),
            dmc.NumberInput(
                label="Number of Populations",
                id='pop-num-populations',
                value=2,
                min=1,
                max=5,
                step=1,
            ),
            dmc.Select(
                label='Parametric Distance Model',
                id='pop-dd-model',
                data=parametric_models,
                value='dd_gauss',
                clearable=False,
                allowDeselect=False,
            ),
            dmc.Space(h=10),
            distance_slider(page_id),
            dmc.Space(h=10),
            # dmc.Paper([
                dmc.Accordion(
                    children=[
                        dmc.AccordionItem(
                            [
                                dmc.AccordionControl("Advanced Fit Options"),
                                dmc.AccordionPanel(adv_fit_options_parametric(page_id))
                            ],
                            value="adv-options"
                        )
                    ]
                ),
            # ], withBorder=True, className="mb-3"),
            
            dmc.Space(h=10),
            
            fit_save_download_buttons(page_id),
            html.Div(id='pop-fit-status')
        ], width=3),
        
        dbc.Col([
            html.Div([
            dmc.Paper([
                    dcc.Graph(id={"type": "fit-plot", "page": page_id},
                            figure=plotly_deerlab(None),
                            style={'height': '100%'},
                            config={'responsive': True})
                            ],
                            style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 300}),
            dmc.Paper([
                    dmc.Tabs([dmc.TabsList([
                        dmc.TabsTab("Population Overview", value="pop-overview"),
                        dmc.TabsTab("Fit Results", value="FitResults"),
                        dmc.TabsTab("Goodness of Fit", value="gof"),
                        dmc.TabsTab("Dist. Stats", value="dist-stats")
                        ]),
                        dmc.TabsPanel(value="pop-overview", children=[],
                                      style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0, 'overflow': 'hidden'}),
                        dmc.TabsPanel(value="FitResults", children=[
                            dmc.CodeHighlight(id={"type":"fit-results-code", "page":page_id},code=default_fit_results_code, language="python")],style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'}),
                        dmc.TabsPanel(value="gof", children=[dcc.Graph(id={"type":"gof-plot", "page":page_id}, figure=plotly_goodness_of_fit(),style={'height': '100%'},config={'responsive': True})],style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0}),
                        dmc.TabsPanel(value="dist-stats", children=[
                            dmc.Table(
                            id={"type":"dist-stats-table", "page":page_id},
                            data={
                                "head": ["Statistic", "Value", "Confidence Interval (95%)"],
                            },
                            striped=True,
                            highlightOnHover=True,
                        )],style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'}),
                        ],style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0},
                        value="pop-overview"),
                    ], variant="outline",
                    style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0, 'overflow': 'hidden'})
                ], style={'display': 'flex', 'flexDirection': 'column', 'height': 'calc(100vh - 160px)', 'gap': '12px'})
                    
        ], width=9)
        
    ]),
    dcc.Store(id='pop-fit-results-store')
    # Hidden store for fit results
    
])

clientside_callback(
        """
        function updateLoadingState(n_clicks) {
            return true
        }
        """,
        Output("pop-run-fit-btn", "loading", allow_duplicate=True),
        Input("pop-run-fit-btn", "n_clicks"),
        prevent_initial_call=True,
    )



@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, "error", allow_duplicate=True),
    Input({'type': 'dataset-dropdown', 'page': page_id}, "value"),
    prevent_initial_call=True
)
def check_dataset_input(ds_inputs):
    # Check that between 2 and 5 datasets are selected, otherwise show an error message
    if not ds_inputs:
        return None
    elif len(ds_inputs) < 2:
        return "Please select at least 2 datasets."
    elif len(ds_inputs) > 5:
        return "Please select no more than 5 datasets."
    else:
        return None
    
@callback(
    Output({'type': 'dataset-dropdown', 'page': page_id}, 'data'),
    Input('url', 'pathname')
)
def update_dropdown(pathname):
    session = get_session()
    datasets = session.query(Dataset).all()
    options = [{'label': ds.name, 'value': str(ds.id)} for ds in datasets]
    session.close()
    return options


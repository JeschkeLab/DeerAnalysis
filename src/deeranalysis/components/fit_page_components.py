import dash_mantine_components as dmc
from dash_iconify import DashIconify
from deeranalysis.utils.deerlab_options import regparam_options, plotly_deerlab, plotly_goodness_of_fit

from dash import dcc,html

DEFAULT_FIT_RESULTS_CODE = """Fit Resuls will be displayed here after running the fit. \nThis can include parameters like mean distance, width, and any other relevant metrics."""

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


def distance_slider(page_id):
    return dmc.Stack([dmc.Text("Distance Axis (nm): ", size="md", fw=500, mb=4),
        dcc.RangeSlider(
                id= {"type": "distance-axis", "page": page_id},
                min=1.5,
                max=12,
                step=0.25,
                value=[1.75, 6],
                marks={i: f'{i}' for i in range(1, 13)},
                allowCross=False,
                allow_direct_input=True,
                className="dmc"
            )],gap=2,)

# def distance_slider(page_id):
#     return dcc.RangeSlider(
#                     id= {"type": "distance-axis", "page": page_id},
#                     min=1.5,
#                     max=12,
#                     step=0.5,
#                     value=[1.5, 6],
#                     marks={i: f'{i}' for i in range(1, 13)},
#                     allowCross=False,
#                     allow_direct_input=True,
#                     className="dmc"
#             )

def fit_results_tab(page_id):
    """
    Creates the Fit Results tab panel for the fit results tabs. This will display the fit results code after running a fit.
    The panel contains a dmc.CodeHighlight component that will display the fit results as code after running the fit.
    
    Parameters:
    -----------
    page_id: string, the id of the page to use for the fit results code component

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Fit Results tab. 
    The TabsTab will have the label "Fit Results" and the TabsPanel will contain a dmc.CodeHighlight component with id {"type": "fit-results-code", "page": page_id} and default code set to DEFAULT_FIT_RESULTS_CODE.
    """

    tabstab = dmc.TabsTab("Fit Results", value="FitResults")

    panel =  dmc.TabsPanel(value="FitResults", children=[
        dmc.CodeHighlight(
            id={"type": "fit-results-code", "page": page_id},
            code=DEFAULT_FIT_RESULTS_CODE,
            language="bash",
        )
    ], style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'})
    return tabstab, panel


def goodness_of_fit_tab(page_id):
    """
    Creates the Goodness of Fit tab panel for the fit results tabs. This will display a plot of goodness-of-fit metrics after running a fit.
    The panel contains a dcc.Graph component that will display the goodness-of-fit plot after running the fit.

    Parameters:
    -----------
    page_id: string, the id of the page to use for the goodness-of-fit plot

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Goodness of Fit tab. 
    The TabsTab will have the label "Goodness of Fit" and the TabsPanel will contain a dcc.Graph component with id {"type": "gof-plot", "page": page_id} 
    and default figure set to plotly_goodness_of_fit(). The TabsPanel will have styles set to make it flexible and responsive.
    """

    tabstab = dmc.TabsTab("Goodness of Fit", value="gof")
    panel = dmc.TabsPanel(value="gof", children=[
        dcc.Graph(
            id={"type": "gof-plot", "page": page_id},
            figure=plotly_goodness_of_fit(),
            style={'height': '100%'},
            config={'responsive': True},
        )
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0})
    return tabstab, panel


def dist_stats_tab(page_id):
    """
    Creates the Distance Statistics tab panel for the fit results tabs. This will display a table of distance distribution statistics after running a fit.
    The panel contains a dmc.Table component that will display the distance distribution statistics after running the fit.  

    Parameters:
    -----------
    page_id: string, the id of the page to use for the distance statistics table

    Returns:
    -----------
    tuple: (dmc.TabsTab, dmc.TabsPanel) for the Distance Statistics tab.
    The TabsTab will have the label "Dist. Stats" and the TabsPanel will contain a dmc.Table component with id {"type": "dist-stats-table", "page": page_id}
    and default data set to a table header with "Statistic", "Value", and "Confidence Interval (95%)". The TabsPanel will have styles set to make it flexible and responsive.

    """

    tabstab = dmc.TabsTab("Dist. Stats", value="dist-stats")

    panel =  dmc.TabsPanel(value="dist-stats", children=[
        dmc.Table(
            id={"type": "dist-stats-table", "page": page_id},
            data={
                "head": ["Statistic", "Value", "Confidence Interval (95%)"],
            },
            striped=True,
            highlightOnHover=True,
        )
    ], style={'flex': '1', 'minHeight': 0, 'overflow': 'auto'})
    return tabstab, panel


# def fit_results_tabs(page_id):
#     return dmc.Paper([
#         dmc.Tabs([
#             dmc.TabsList([
#                 dmc.TabsTab("Fit Results", value="FitResults"),
#                 dmc.TabsTab("Goodness of Fit", value="gof"),
#                 dmc.TabsTab("Dist. Stats", value="dist-stats"),
#             ]),
#             fit_results_tab(page_id),
#             goodness_of_fit_tab(page_id),
#             dist_stats_tab(page_id),
#         ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0}),
#     ], variant="outline",
#     style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0, 'overflow': 'hidden'})


def fit_results_tabs(*tabs):
    """
    Creates a Mantine Paper component containing Tabs for the given tabs. Defaults value to the first tab provided.

    Parameters:
    *tabs: tuples of (dmc.TabsTab, dmc.TabsPanel) to include in the Tabs component
    
    returns:
    dmc.Paper containing the Tabs component with the specified tabs
    """
    tab_tabs = [tabs[i][0] for i in range(len(tabs))]
    tab_panels = [tabs[i][1] for i in range(len(tabs))]
    tab0_value = tabs[0][0].value if len(tabs) > 0 else None

    return dmc.Paper([
                    dmc.Tabs([
                        dmc.TabsList(tab_tabs),
                        *tab_panels
                        ], 
                    style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0}, value=tab0_value)
                    ], variant="outline",
                    style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 0, 'overflow': 'hidden'})




def fit_plot(page_id):
    return dmc.Paper([
                    dcc.Graph(id={"type": "fit-plot", "page": page_id},
                            figure=plotly_deerlab(None),
                            style={'height': '100%'},
                            config={'responsive': True})
                            ],
                            style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 300})



# ----- Callbacks for Global and Population Fitting Pages -----


def plotly_deerlab_pagation(*datasets, page_id):
    """
    For globally fit datasets, creates a plotly figure using the plotly deerlab function for each dataset and combines them
    into a single element with a dmc.Pagination component to navigate between them. This is encapsulated in a dmc.Paper just like the fit_plot function. 
    The pagination component will have as many pages as there are datasets, and the figure will update to show the corresponding dataset when a page is selected.

    If no datasets are provided, returns a default plotly deerlab figure but still with a pagination element.
    """
    if datasets:
        figures = [plotly_deerlab(ds) for ds in datasets]
        initial_figure = figures[0]
        total_pages = len(figures)
    else:
        figures = [plotly_deerlab(None)]
        initial_figure = figures[0]
        total_pages = 1

    # Store serialized figures so a clientside callback can swap them
    figures_json = [fig.to_json() for fig in figures]

    return dmc.Paper([
        dcc.Store(
            id={"type": "fit-plot-figures-store", "page": page_id},
            data=figures_json,
        ),
        dcc.Graph(
            id={"type": "fit-plot", "page": page_id},
            figure=initial_figure,
            style={'height': '100%'},
            config={'responsive': True},
        ),
        dmc.Center(
            dmc.Pagination(
                id={"type": "fit-plot-pagination", "page": page_id},
                total=total_pages,
                value=1,
                withEdges=True,
            ),
            mt="xs",
        ),
    ], style={'flex': '1', 'display': 'flex', 'flexDirection': 'column', 'minHeight': 300})



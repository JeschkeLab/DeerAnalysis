import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, no_update, MATCH, ALL, ctx
import dash


dash.register_page(__name__)
page_id = 'citation'


def truncate_authors(authors, max_shown=4):
    if len(authors) <= max_shown:
        return authors
    return [authors[0], authors[1], "...", authors[-1]]


def paper_card(title: str, authors: list, journal, year, doi, image=None):
    display_authors = truncate_authors(authors)
    author_items = []
    for a in display_authors:
        if a == "...":
            author_items.append(dmc.Text("...", size="md", c="dimmed", style={"lineHeight": "24px"}))
        else:
            author_items.append(dmc.Badge(a, variant="light", size="md"))

    doi_link = dmc.Anchor(f"DOI: {doi}", href=f"https://doi.org/{doi}", target="_blank", size="md")

    if image == 0:
        image_component = dmc.Space(h=10)
    elif image:
        image_component = dmc.Image(src=image, alt=f"Abstract image for {title}", h=150, fit="contain")
    else:
        image_component = html.Div(style={"height": 150})

    return dmc.Card(
        children=[
            dmc.CardSection(
                dmc.Text(title, size="md", fw=700, p="md", lh=1.4),
                style={"backgroundColor": "var(--mantine-color-blue-light)"},
                withBorder=True,
            ),
            dmc.Stack(
                [
                    image_component,
                    dmc.Group(author_items, gap="xs"),
                    dmc.Text(f"{journal}, {year}", size="md", c="dimmed"),
                    doi_link,
                ],
                gap="xs",
                p="md",
                justify="flex-end",
                style={"flex": 1},
            ),
        ],
        shadow="sm",
        radius="md",
        withBorder=True,
        style={"height": "100%", "display": "flex", "flexDirection": "column"},
    )


layout = dmc.Container(
    style={"maxWidth": 960},
    children=[
        dmc.Title("Citing DeerAnalysis 2026", order=1, mb="md"),
        dmc.Text(
            "Citing scientific software is an important step in acknowledging the work of developers and ensuring "
            "that they receive credit for their contributions. Scientific software often struggles to receive funding "
            "and recognition, and proper citation can help address this issue.",
            mb="xs",size="md",
        ),
        dmc.Text(
            "In the case of DeerAnalysis 2026, we kindly ask that you cite not only this piece of software but the "
            "core fitting libraries as well: DeerLab and DeerNet (if used):",
            mb="md",size="md",
        ),
        dmc.SimpleGrid(
            cols=3,
            spacing="md",
            mb="xl",
            children=[
                paper_card(
                    title="DeerAnalysis 2026:",
                    authors=['Hugo Karas', 'Gunnar Jeschke'],
                    journal="In-Preparation",
                    image=None,
                    year=2026,
                    doi="TBA",
                ),
                paper_card(
                    title="DeerLab: a comprehensive software package for analyzing dipolar electron paramagnetic resonance spectroscopy data",
                    authors=['Luis Fábregas Ibáñez', 'Gunnar Jeschke', 'Stefan Stoll'],
                    journal="Magnetic Resonance",
                    image="/assets/paper_figures/DeerLab_paper_abstract.png",
                    year=2020,
                    doi="10.5194/mr-1-209-2020",
                ),
                paper_card(
                    title="Deep neural network processing of DEER data",
                    authors=['Steven G. Worswick', 'James A. Spencer', 'Gunnar Jeschke', 'Ilya Kuprov'],
                    journal="Science Advances",
                    year=2018,
                    doi="10.1126/sciadv.aat5218",
                ),
            ],
        ),
        dmc.Text(
            "The DeerLab and DeerNet projects also generated other publications that might be relevant or interesting:",
            mb="xs",size="md",
        ),
        dmc.Accordion(
            mb="xl",
            children=dmc.AccordionItem(
                value="related-papers",
                children=[
                    dmc.AccordionControl(dmc.Title("Related publications",order=3)),
                    dmc.AccordionPanel(
                        dmc.SimpleGrid(
                            cols=3,
                            spacing="md",
                            children=[
                                paper_card(
                                    title="Dipolar pathways in dipolar EPR spectroscopy",
                                    authors=['Luis Fábregas Ibáñez', 'Maxx H. Tessmer', 'Gunnar Jeschke', 'Stefan Stoll'],
                                    image="/assets/paper_figures/dipolar_paper_abstract.gif",
                                    journal="Phys. Chem. Chem. Phys", year=2022, doi="10.1039/D1CP03305K",
                                ),
                                paper_card(
                                    title="Dipolar pathways in multi-spin and multi-dimensional dipolar EPR spectroscopy",
                                    authors=['Luis Fábregas Ibáñez', 'Valerie Mertens', 'Irina Ritsch', 'Tona von Hagens', 'Gunnar Jeschke', 'Stefan Stoll'],
                                    image="/assets/paper_figures/multi_dipolar_paper_abstract.gif",
                                    journal="Phys. Chem. Chem. Phys", year=2022, doi="10.1039/D2CP03048A",
                                ),
                                paper_card(
                                    title="Compactness regularization in the analysis of dipolar EPR spectroscopy data",
                                    authors=['Luis Fábregas Ibáñez', 'Gunnar Jeschke', 'Stefan Stoll'],
                                    image="/assets/paper_figures/compactness_paper_abstract.jpg",
                                    journal="Journal of Magnetic Resonance", year=2022, doi="10.1016/j.jmr.2022.107218",
                                ),
                                paper_card(
                                    title="Neural networks in pulsed dipolar spectroscopy: A practical guide",
                                    image="/assets/paper_figures/DeerNet2_paper_abstract.jpg",
                                    authors=['Jake Keeley', 'Tajwar Choudhury', 'Laura Galazzo', 'Enrica Bordignon', 'Akiva Feintuch', 'Daniella Goldfarb', 'Hannah Russell', 'Michael J. Taylor', 'Janet E. Lovett', 'Andrea Eggeling', 'Luis Fábregas Ibáñez', 'Katharina Keller', 'Maxim Yulikov', 'Gunnar Jeschke', 'Ilya Kuprov'],
                                    journal="Journal of Magnetic Resonance", year=2022, doi="10.1016/j.jmr.2022.107186",
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ),
        dmc.Text(
            "Historic DeerAnalysis publications can be found below. \n Please note that these publications refer to "
            "previous versions of the software, and may not be directly relevant to DeerAnalysis 2026. However, "
            "they provide important context and background for the development of the software.",
            mb="xs",size="md",
        ),
        dmc.Accordion(
            mb="xl",
            children=dmc.AccordionItem(
                value="historical-papers",
                children=[
                    dmc.AccordionControl(dmc.Title("Historical publications",order=3)),
                    dmc.AccordionPanel(
                        dmc.SimpleGrid(
                            cols=3,
                            spacing="md",
                            children=[
                                paper_card(
                                    title="DeerAnalysis2006-a Comprehensive Software Package for Analyzing Pulsed ELDOR Data",
                                    authors=['G Jeschke', 'V. Chechik', 'P. Ionita', 'A. Godt', 'H. Zimmermann', 'J. Banham','C. Timmel', 'D. Hilger', 'H. Jung'],
                                    image=0,
                                    journal="Appl. Magn. Reson", year=2022, doi="10.1007/bf03166213",
                                ),]
                        ),
                    ),
                ],
            ),
        ),
    ],
)

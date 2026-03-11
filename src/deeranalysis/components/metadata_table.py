from dash import html
import dash_mantine_components as dmc

MAX_LEN = 80  # Max length before truncation in the table



def metadata_long_values_model(page_id):
    return html.Div([
        dmc.Modal(
            id={"type": "metadata-value-modal",  "page": page_id},
            title="Full Value",
            children=[
                    dmc.Textarea(
                        id={"type":"metadata-value-modal-text",  "page": page_id},
                        value="",
                        readOnly=True,
                        autosize=True,
                        style={"width": "100%", "fontFamily": "monospace"},
                    ),
                # )
            ],
            size="70%",
            opened=False,
        )])


def make_value_cell(key, value,long_values_store):
    val_str = str(value)
    if len(val_str) > MAX_LEN:
        long_values_store[key] = val_str
        return html.Td([
            html.Span(
                val_str[:MAX_LEN] + "…",
                style={"marginRight": "8px", "fontFamily": "monospace"},
            ),
            dmc.Button(
                "Show",
                id={"type": "metadata-show-btn", "key": key},
                size="compact-xs",
                variant="subtle",
                n_clicks=0,
            ),
        ])
    return html.Td(val_str, style={"fontFamily": "monospace"})

def build_table_rows(items_dict,long_values_store):
    rows = []
    for key, value in items_dict.items():
        rows.append(html.Tr([
            html.Td(html.Strong(str(key)), style={"whiteSpace": "nowrap", "paddingRight": "16px"}),
            make_value_cell(key, value,long_values_store),
        ]))
    return rows
def build_metadata_section(dataset,delays=True):
    """Build the metadata & delays section children for a dataset.

    Returns a tuple of (children, long_values_store) where:
      - children is a list of Dash components to render
      - long_values_store is a dict mapping key -> full string value (for the modal)
    """
    long_values_store = {}

    metadata_sections = []

    if dataset.meta:
        try:
            rows = build_table_rows(dataset.meta,long_values_store)
            # metadata_sections.append(dmc.Title("Metadata", order=5, mb="xs"))
            metadata_sections.append(
                dmc.Table(
                    children=[html.Tbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                    mb="md",
                )
            )
        except Exception:
            metadata_sections.append(html.P("Unable to parse metadata."))
    else:
        metadata_sections.append(html.P("No metadata available.", className="text-muted"))

    if dataset.delays and delays:
        try:
            rows = build_table_rows(dataset.delays,long_values_store)
            metadata_sections.append(dmc.Divider(my="sm"))
            metadata_sections.append(dmc.Title("Delays", order=5, mb="xs"))
            metadata_sections.append(
                dmc.Table(
                    children=[html.Tbody(rows)],
                    striped=True,
                    highlightOnHover=True,
                    withTableBorder=True,
                    withColumnBorders=True,
                )
            )
        except Exception:
            metadata_sections.append(html.P("Unable to parse delays."))
    elif not dataset.delays and delays:
        metadata_sections.append(html.P("No delays available.", className="text-muted"))

    return html.Div(metadata_sections, style={"padding": "8px"}), long_values_store



def build_delays_table(dataset):
    rows = build_table_rows(dataset.delays)
    return dmc.Table(
        children=[html.Tbody(rows)],
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=True,
    )
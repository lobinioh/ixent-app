import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def PlotIterator(
    data_to_process,
    xTag,
    y_tags1,
    y_tags2,
    ref_mode,
    plot_type,
    line_mode,
    color_iterator,
    style_iterator,
    marker_iterator,
    filter_iterator,
    colormap_iterator,
    n_clicks2,
    filename,
    yTag_criterion,
    yaxes_criterion,
    markerSize,
    lineSize,
    row_iterator,
    column_iterator,
    fig_w,
    fig_h,
):

    # 🔒 Sicherheit
    if data_to_process is None or data_to_process.empty:
        fig = go.Figure()
        return fig, pd.DataFrame(), ["OFF", []]

    df = data_to_process.copy()

    # 👉 Filter anwenden
    if filter_iterator.get("tag") != "all" and "restrict" in filter_iterator:
        df = df[df[filter_iterator["tag"]].isin(filter_iterator["restrict"])]

    # 👉 Figure erstellen
    fig = make_subplots(rows=1, cols=1)

    # 👉 Linienmodus bestimmen
    if line_mode == "line":
        mode = "lines"
    elif line_mode == "marker":
        mode = "markers"
    elif line_mode == "line & marker":
        mode = "lines+markers"
    else:
        mode = "lines"

    # 👉 Primary Y
    if y_tags1:
        for y in y_tags1:
            if y in df.columns and xTag in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df[xTag],
                        y=df[y],
                        mode=mode,
                        name=f"{y}",
                        marker=dict(size=markerSize),
                        line=dict(width=lineSize),
                    )
                )

    # 👉 Secondary Y
    if y_tags2:
        for y in y_tags2:
            if y in df.columns and xTag in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df[xTag],
                        y=df[y],
                        mode=mode,
                        name=f"{y} (secondary)",
                        marker=dict(size=markerSize),
                        line=dict(width=lineSize, dash="dash"),
                    )
                )

    # 👉 Layout
    fig.update_layout(
        template="plotly_white",
        height=fig_h if fig_h else 600,
        width=fig_w if fig_w else 900,
        title="Plot",
    )

    # 👉 CSV Output (für Download)
    output_df = df.copy()

    return fig, output_df, ["OFF", []]
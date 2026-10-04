"""Charts used by the Streamlit app."""

from collections.abc import Mapping
from typing import Final

import altair as alt
import pandas as pd

LABEL_INK: Final = "#0b0b0b"  # in-segment labels; legible on every style color in both themes
MIN_LABELED_SHARE: Final = 0.08  # narrower segments rely on the tooltip and legend
ROW_HEIGHT: Final = 52
CHROME_HEIGHT: Final = 70  # legend above plus axis below


def chart_height(n_rows: int) -> int:
    """Total pixel height of `mix_bars` for n rows; Streamlit fits legend and axes inside it."""
    return ROW_HEIGHT * n_rows + CHROME_HEIGHT


def _segments(mixes: pd.DataFrame) -> pd.DataFrame:
    """Long frame of bar segments with their start and end positions along a 0-1 bar."""
    shares = mixes.div(mixes.sum(axis=1), axis=0)
    end = shares.cumsum(axis=1)
    return pd.concat(
        {"share": shares.stack(), "start": (end - shares).stack(), "end": end.stack()}, axis=1
    ).rename_axis(["version", "style"]).reset_index()


def mix_bars(mixes: pd.DataFrame, colors: Mapping[str, str], surface: str) -> alt.LayerChart:
    """100% stacked bars: one row per version (the index, top to bottom), split into style
    shares (the columns, left to right).

    Args:
        mixes: Non-negative shares per row; each row is normalized to sum to 1.
        colors: Style (column) -> fill color.
        surface: Page background color, used for the gap between segments.
    """
    segments = _segments(mixes)
    styles, versions = list(mixes.columns), list(mixes.index)
    y = alt.Y(
        "version:N", sort=versions, title=None, scale=alt.Scale(paddingInner=0.25, paddingOuter=0.1),
        axis=alt.Axis(labelFontSize=12, ticks=False, domain=False, labelOverlap=False),
    )
    bars = alt.Chart(segments).mark_bar(stroke=surface, strokeWidth=2, height={"band": 1}).encode(
        y=y,
        x=alt.X("start:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", title=None, tickCount=4)),
        x2="end:Q",
        color=alt.Color(
            "style:N", scale=alt.Scale(domain=styles, range=[colors[s] for s in styles]),
            legend=alt.Legend(orient="top", title=None, labelFontSize=12),
        ),
        tooltip=[
            alt.Tooltip("version:N", title="Recipe"),
            alt.Tooltip("style:N", title="Style"),
            alt.Tooltip("share:Q", title="Share", format=".0%"),
        ],
    )
    labels = alt.Chart(segments[segments["share"] >= MIN_LABELED_SHARE]).mark_text(
        color=LABEL_INK, fontSize=12, fontWeight=600,
    ).encode(
        y=y,
        x=alt.X("mid:Q", scale=alt.Scale(domain=[0, 1])),
        text=alt.Text("share:Q", format=".0%"),
    ).transform_calculate(mid="(datum.start + datum.end) / 2")
    return (bars + labels).properties(height=chart_height(len(versions)))

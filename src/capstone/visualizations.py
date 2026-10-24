"""Report figures: one house style and a function for each figure family.

Call `set_theme()` once at the top of a Quarto document. Every figure function returns a
matplotlib Figure sized for the page (`FULL_WIDTH` is the 6.5 in text block of letter paper
with 1 in margins), so text prints at its true size. Figures carry no titles of their own:
captions belong in Quarto (`#| fig-cap:`), and panel titles only name small multiples.

Color rules, applied everywhere:
- Hue means style. Neapolitan, New York and Sicilian keep the app's colors (`PLOT.style_colors`,
  the first three slots of a palette validated for color-vision deficiency).
- Anything that is not a style (models, metrics, before/after) is drawn in neutral inks and
  told apart by position, marker, line style and direct labels, so it survives grayscale print.
- Magnitudes use one blue ramp (`SEQUENTIAL`); signed values such as z-scores use a
  blue-gray-red map centered on zero (`DIVERGING`).
"""

from collections.abc import Callable, Mapping, Sequence
from math import ceil
from pathlib import Path
from typing import Final, Literal

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from cycler import cycler
from matplotlib.axes import Axes
from matplotlib.colors import Colormap, LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline

from capstone.config import CATEGORICAL, NUMERIC, PATHS, PLOT, STYLES, Col, label
from capstone.features import feature_name
from capstone.models.centroids import centroids

# -- page geometry and type -------------------------------------------------

FULL_WIDTH: Final = 6.5  # inches: letter paper, 1 in margins (set `geometry: margin=1in` in Quarto)
HALF_WIDTH: Final = 3.15  # two figures side by side with a gutter
BASE_FONT_SIZE: Final = 9.0
FONT_FAMILY: Final = ["Helvetica Neue", "Arial", "Liberation Sans", "DejaVu Sans"]  # macOS, Windows, Linux; first installed wins

# -- ink and chrome (reference palette, light mode) -------------------------

INK: Final = "#0b0b0b"
INK_SECONDARY: Final = "#52514e"
INK_MUTED: Final = "#898781"
GRID: Final = "#e1e0d9"
EMPTY_CELL: Final = "#f3f2ef"  # heatmap cells with no value (NaN)
AXIS: Final = "#c3c2b7"
SURFACE: Final = "#ffffff"  # the printed page; also the 1.5 pt gap between adjacent fills

# neutral series for non-style lines: color, line style, marker
NEUTRAL_SERIES: Final = (
    (INK, "-", "o"),
    (INK_SECONDARY, "--", "s"),
    (INK_MUTED, ":", "^"),
    (INK, "-.", "D"),
)

# -- color scales -----------------------------------------------------------

BLUE_RAMP: Final = (
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
)  # steps 100-700, light to dark
SEQUENTIAL: Final = LinearSegmentedColormap.from_list("capstone_sequential", BLUE_RAMP)
DIVERGING: Final = LinearSegmentedColormap.from_list(
    "capstone_diverging", ["#0d366b", "#3987e5", "#f0efec", "#e34948", "#8a1c1c"]
)  # blue (below) - neutral gray - red (above)

MIN_LABELED_SHARE: Final = 0.08  # narrower stacked-bar segments go unlabeled


# -- theme and helpers ------------------------------------------------------


def set_theme(base_size: float = BASE_FONT_SIZE) -> None:
    """Apply the report style to every later matplotlib figure and register the colormaps
    (as "capstone_sequential" and "capstone_diverging", plus their "_r" reverses)."""
    for cmap in (SEQUENTIAL, DIVERGING):
        for c in (cmap, cmap.reversed()):
            if c.name not in mpl.colormaps:
                mpl.colormaps.register(c)
    mpl.rcParams.update({
        # type
        "font.family": "sans-serif",
        "font.sans-serif": FONT_FAMILY,
        "font.size": base_size,
        "axes.titlesize": base_size,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 6,
        "axes.labelsize": base_size,
        "axes.labelcolor": INK_SECONDARY,
        "xtick.labelsize": base_size - 1,
        "ytick.labelsize": base_size - 1,
        "legend.fontsize": base_size - 1,
        "figure.titlesize": base_size + 1,
        "figure.labelsize": base_size,
        "text.color": INK,
        # recessive chrome
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": AXIS,
        "ytick.color": AXIS,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "legend.frameon": False,
        "legend.handlelength": 1.2,
        "legend.handletextpad": 0.4,
        "legend.columnspacing": 1.2,
        # marks
        "axes.prop_cycle": cycler(color=[c for c, _, _ in NEUTRAL_SERIES[:3]]),
        "lines.linewidth": 1.5,
        "lines.markersize": 4.5,
        "patch.linewidth": 0,
        "image.cmap": SEQUENTIAL.name,
        # canvas and output
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.figsize": (FULL_WIDTH, FULL_WIDTH * 0.6),
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "figure.constrained_layout.use": True,
        "pdf.fonttype": 42,  # embed TrueType so PDF text stays selectable and editable
        "ps.fonttype": 42,
    })


def figsize(width: Literal["full", "half"] | float = "full", aspect: float = 0.6) -> tuple[float, float]:
    """(width, height) in inches: "full" or "half" page width, or inches; height = width x aspect."""
    w = {"full": FULL_WIDTH, "half": HALF_WIDTH}[width] if isinstance(width, str) else float(width)
    return w, w * aspect


def save(fig: Figure, name: str, formats: Sequence[str] = ("pdf", "png"), directory: Path = PATHS.figures) -> list[Path]:
    """Write a figure to <directory>/<name>.<ext> for each format (for slides or reuse
    outside Quarto, which embeds figures itself) and return the paths."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"{name}.{ext}" for ext in formats]
    for path in paths:
        fig.savefig(path)
    return paths


def style_color(style: str) -> str:
    """The fixed color of a style."""
    return PLOT.style_colors[style]


def _is_style(value: object) -> bool:
    return str(value) in {str(s) for s in STYLES}


def _ordered_groups(values: pd.Series) -> list[str]:
    """Group names in display order: styles in STYLES order, anything else sorted."""
    present = list(pd.unique(values))
    if all(_is_style(v) for v in present):
        return [str(s) for s in STYLES if str(s) in present]
    return sorted(present)


def _group_colors(groups: Sequence[str]) -> dict[str, str]:
    """Style colors for styles; one neutral ink for anything else (its axis label identifies it)."""
    return {g: style_color(g) if _is_style(g) else INK_SECONDARY for g in groups}


def _style_handles(styles: Sequence[str], marker: str = "o") -> list[Line2D]:
    return [
        Line2D([], [], marker=marker, linestyle="", markersize=6, markerfacecolor=style_color(s),
               markeredgecolor=SURFACE, label=label(s))
        for s in styles
    ]


def _top_legend(ax: Axes, handles: Sequence | None = None, ncols: int | None = None) -> None:
    """Legend in one row above the plot area, left-aligned with it."""
    handles = list(handles) if handles is not None else ax.get_legend_handles_labels()[0]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.01), ncols=ncols or len(handles),
              borderaxespad=0, frameon=False)


def _rotate_xticklabels(ax: Axes, rotation: float = 35) -> None:
    for t in ax.get_xticklabels():
        t.set_rotation(rotation)
        t.set_horizontalalignment("right")
        t.set_rotation_mode("anchor")


def _ink_on(rgba: Sequence[float]) -> str:
    """Text color legible on a fill: white on dark fills, ink on light ones."""
    r, g, b = rgba[:3]
    return SURFACE if 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.5 else INK


def _new_axes(ax: Axes | None, size: tuple[float, float]) -> Axes:
    return plt.subplots(figsize=size)[1] if ax is None else ax


# -- building blocks --------------------------------------------------------


def strip_box(
    ax: Axes,
    groups: Mapping[str, Sequence[float]],
    colors: Mapping[str, str] | None = None,
    *,
    point_size: float = 16,
    jitter: float = 0.13,
    seed: int = 0,
) -> Axes:
    """Horizontal box plots (median, IQR, whiskers to 1.5 IQR) over the jittered raw points,
    one row per group with the first group on top. Shows every observation, which matters
    at this sample size, while the box summarizes it.
    """
    names = list(groups)
    colors = colors or _group_colors(names)
    pos = np.arange(len(names))[::-1]
    data = [np.asarray(groups[n], dtype=float) for n in names]
    data = [d[~np.isnan(d)] for d in data]
    line = {"color": INK_SECONDARY, "linewidth": 0.8}
    ax.boxplot(
        data, positions=pos, orientation="horizontal", widths=0.55, showfliers=False,
        boxprops=line, whiskerprops=line, capprops={"linewidth": 0}, medianprops={"color": INK, "linewidth": 1.4},
    )
    rng = np.random.default_rng(seed)
    for p, d, n in zip(pos, data, names):
        ax.scatter(d, p + rng.uniform(-jitter, jitter, len(d)), s=point_size, color=colors[n],
                   edgecolor=SURFACE, linewidth=0.5, alpha=0.9, zorder=3)
    ax.set_yticks(pos, [label(n) for n in names])
    ax.set_ylim(-0.6, len(names) - 0.4)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    return ax


def _heat(
    ax: Axes, frame: pd.DataFrame, cmap: Colormap, norm: Normalize,
    fmt: str | Callable[[float], str] | None, text_size: float,
):
    """Cells with a 1.5 pt surface gap between them and optional in-cell values; NaN cells
    are drawn in a neutral gray and left unlabeled."""
    values = frame.to_numpy(dtype=float)
    image = ax.imshow(values, cmap=cmap.with_extremes(bad=EMPTY_CELL), norm=norm, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(frame.shape[1]), [label(c) for c in frame.columns])
    ax.set_yticks(range(frame.shape[0]), [label(i) for i in frame.index])
    ax.set_xticks(np.arange(-0.5, frame.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, frame.shape[0]), minor=True)
    ax.tick_params(which="both", length=0)
    ax.grid(False)
    ax.grid(which="minor", visible=True, color=SURFACE, linewidth=1.5)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if fmt is not None:
        for (i, j), v in np.ndenumerate(values):
            text = "" if np.isnan(v) else fmt(v) if callable(fmt) else fmt.format(v)
            if text:
                ax.text(j, i, text, ha="center", va="center", fontsize=text_size, color=_ink_on(cmap(norm(v))))
    return image


def heatmap(
    frame: pd.DataFrame,
    ax: Axes | None = None,
    *,
    diverging: bool = False,
    vmin: float | None = None,
    vmax: float | None = None,
    fmt: str | Callable[[float], str] | None = "{:.2f}",
    colorbar_label: str | None = None,
    text_size: float = BASE_FONT_SIZE - 1.5,
) -> Figure:
    """Annotated heatmap of a frame (rows and columns labeled through `label`).

    Args:
        diverging: Center the blue-gray-red map on zero, symmetric around it.
        fmt: Format string or function for cell text; None hides values.
        colorbar_label: Adds a colorbar with this label (worth it when fmt is None).
    """
    values = frame.to_numpy(dtype=float)
    size = (min(FULL_WIDTH, 0.6 * frame.shape[1] + 1.8), 0.3 * frame.shape[0] + 1.0)
    ax = _new_axes(ax, size)
    if diverging:
        lim = max(abs(v) for v in (vmin, vmax, np.nanmin(values), np.nanmax(values)) if v is not None)
        norm, cmap = Normalize(-lim, lim), DIVERGING
    else:
        norm = Normalize(np.nanmin(values) if vmin is None else vmin, np.nanmax(values) if vmax is None else vmax)
        cmap = SEQUENTIAL
    image = _heat(ax, frame, cmap, norm, fmt, text_size)
    if max((len(label(c)) for c in frame.columns), default=0) > 6:
        _rotate_xticklabels(ax)
    if colorbar_label:
        bar = ax.figure.colorbar(image, ax=ax, shrink=0.85, aspect=25, pad=0.02)
        bar.set_label(colorbar_label)
        bar.outline.set_visible(False)
        bar.ax.tick_params(length=0)
    return ax.figure


def line_plot(
    frame: pd.DataFrame,
    ax: Axes | None = None,
    *,
    xlabel: str | None = None,
    ylabel: str | None = None,
    percent: bool = False,
    direct_labels: bool = True,
    xscale: Literal["linear", "log"] = "linear",
) -> Figure:
    """One neutral line per column against the index (e.g. a metric across a weight sweep).
    Lines differ by ink, dash and marker; with `direct_labels` each is named at its last point
    (nudged apart where lines end close together). Use xscale="log" for doubling sweeps.

    Raises:
        ValueError: With more than four columns; facet the series instead.
    """
    if frame.shape[1] > len(NEUTRAL_SERIES):
        raise ValueError(f"at most {len(NEUTRAL_SERIES)} lines per panel; facet the rest")
    ax = _new_axes(ax, figsize("half", 0.75))
    x = np.arange(len(frame)) if frame.index.dtype == object else frame.index.to_numpy()
    for (name, y), (color, dash, marker) in zip(frame.items(), NEUTRAL_SERIES):
        ax.plot(x, y, color=color, linestyle=dash, marker=marker, label=label(name))
    if xscale == "log":
        ax.set_xscale("log", base=2)
        ax.set_xticks(x, [f"{v:g}" for v in x])
        ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())
    if direct_labels:
        _end_labels(ax, x[-1], frame.iloc[-1])
    if frame.index.dtype == object:
        ax.set_xticks(x, [label(i) for i in frame.index])
    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    if not direct_labels:
        _top_legend(ax)
    ax.set_xlabel(xlabel if xlabel is not None else frame.index.name or "")
    ax.set_ylabel(ylabel or "")
    ax.margins(x=0.04)
    return ax.figure


def _end_labels(ax: Axes, x: float, ends: pd.Series, min_gap: float = 0.075) -> None:
    """Name each line at its last point, spreading labels at least `min_gap` (axes fraction) apart."""
    ax.margins(y=0.08)
    ax.autoscale_view()
    lo, hi = ax.get_ylim()
    frac = ((ends - lo) / (hi - lo)).sort_values()
    placed: list[float] = []
    for v in frac:
        placed.append(max(v, placed[-1] + min_gap) if placed else v)
    shift = max(0.0, placed[-1] - 1.0)  # pull the stack back inside the top edge
    for name, y in zip(frac.index, placed):
        ax.annotate(label(name), (x, y - shift), xycoords=("data", "axes fraction"), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=BASE_FONT_SIZE - 1,
                    color=INK_SECONDARY, annotation_clip=False)


# -- data and features ------------------------------------------------------


def feature_distributions(
    frame: pd.DataFrame,
    features: Sequence[str] = NUMERIC,
    by: str = Col.style,
    *,
    ncols: int | None = None,
    xlabel: str = "Baker's % of flour weight",
) -> Figure:
    """Small multiples of `strip_box`, one panel per feature, grouped by `by` (styles get
    their colors; other groupings, such as real vs synthetic recipes, are neutral)."""
    groups = _ordered_groups(frame[by])
    colors = _group_colors(groups)
    ncols = ncols or len(features)
    nrows = ceil(len(features) / ncols)
    height = nrows * (0.3 * len(groups) + 0.75) + 0.35
    fig, axes = plt.subplots(nrows, ncols, figsize=(FULL_WIDTH, height), sharey=True, squeeze=False)
    for ax, f in zip(axes.flat, features):
        strip_box(ax, {g: frame.loc[frame[by] == g, f] for g in groups}, colors, point_size=11)
        ax.set_title(label(f))
    for ax in axes.flat[len(features):]:
        ax.set_visible(False)
    fig.supxlabel(xlabel, color=INK_SECONDARY)
    return fig


def category_shares(frame: pd.DataFrame, columns: Sequence[str] = CATEGORICAL, by: str = Col.style) -> Figure:
    """Share of each group's recipes using each ingredient type: one heatmap per type
    column, categories ordered by overall frequency, unused combinations in gray."""
    groups = _ordered_groups(frame[by])
    tables = {
        c: pd.crosstab(frame[by], frame[c], normalize="index").reindex(groups)[frame[c].value_counts().index]
        for c in columns
    }
    fig, axes = plt.subplots(
        1, len(columns), figsize=(FULL_WIDTH, 0.3 * len(groups) + 1.55), sharey=True, squeeze=False,
        width_ratios=[t.shape[1] for t in tables.values()],
    )
    for ax, (c, table) in zip(axes.flat, tables.items()):
        _heat(ax, table.mask(table == 0), SEQUENTIAL, Normalize(0, 1), "{:.0%}", BASE_FONT_SIZE - 2)
        ax.set_title(label(c))
        _rotate_xticklabels(ax, 40)
    return fig


def distance_matrix(distances: pd.DataFrame, styles: pd.Series, *, colorbar_label: str = "Distance") -> Figure:
    """Pairwise recipe distances ordered by style, with style blocks outlined. Dark cells are
    similar pairs, so a clean block structure means styles are internally coherent."""
    groups = _ordered_groups(styles)
    order = pd.concat([styles[styles == g].sort_index() for g in groups]).index
    fig, ax = plt.subplots(figsize=figsize(4.6, 0.86))
    image = ax.imshow(distances.loc[order, order].to_numpy(), cmap=SEQUENTIAL.reversed(), vmin=0, interpolation="nearest")
    sizes = np.array([(styles == g).sum() for g in groups])
    edges = np.concatenate([[0], np.cumsum(sizes)]) - 0.5
    for e in edges[1:-1]:
        ax.axhline(e, color=SURFACE, linewidth=1.5)
        ax.axvline(e, color=SURFACE, linewidth=1.5)
    centers = (edges[:-1] + edges[1:]) / 2
    ax.set_xticks(centers, [label(g) for g in groups])
    ax.set_yticks(centers, [label(g) for g in groups], rotation=90, va="center")
    ax.tick_params(length=0)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, shrink=0.8, aspect=25, pad=0.02)
    bar.set_label(colorbar_label)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0)
    return fig


def style_scatter(
    coords: pd.DataFrame,
    styles: pd.Series,
    centers: pd.DataFrame | None = None,
    ax: Axes | None = None,
    *,
    equal_aspect: bool = True,
) -> Figure:
    """2-D embedding (PCA, MDS, ...) colored by style. The first two columns of `coords`
    are plotted and name the axes; `centers` (rows = styles, same columns) adds the
    style centroids as outlined diamonds."""
    ax = _new_axes(ax, figsize("full", 0.62))
    x, y = coords.columns[:2]
    groups = _ordered_groups(styles)
    for g in groups:
        m = (styles == g).reindex(coords.index).to_numpy()
        ax.scatter(coords.loc[m, x], coords.loc[m, y], s=22, color=style_color(g), edgecolor=SURFACE,
                   linewidth=0.6, alpha=0.9, zorder=3)
    handles = _style_handles(groups)
    if centers is not None:
        for g in groups:
            ax.scatter(centers.loc[g, x], centers.loc[g, y], s=90, marker="D", color=style_color(g),
                       edgecolor=INK, linewidth=1.1, zorder=4)
        handles.append(Line2D([], [], marker="D", linestyle="", markersize=7, markerfacecolor=SURFACE,
                              markeredgecolor=INK, label="Style centroid"))
    ax.set_xlabel(label(x))
    ax.set_ylabel(label(y))
    ax.grid(axis="both", visible=True)
    if equal_aspect:
        ax.set_aspect("equal", adjustable="datalim")
    _top_legend(ax, handles)
    return ax.figure


def centroid_heatmap(pipe: Pipeline) -> Figure:
    """Each style centroid's numeric coordinates: the style's average z-score per ingredient,
    i.e. how many standard deviations above or below the all-recipe mean it sits."""
    z = centroids(pipe)[[feature_name(c) for c in NUMERIC]]
    z.columns = list(NUMERIC)
    fig = heatmap(z, diverging=True, fmt="{:+.2f}", colorbar_label="Mean z-score")
    fig.set_size_inches(figsize(4.4, 0.42))
    return fig


# -- classification ---------------------------------------------------------


def cv_scores(
    folds: pd.DataFrame,
    metric: str = "accuracy",
    *,
    model_col: str = "model",
    highlight: str | Sequence[str] | None = None,
    reference: float | None = None,
    reference_label: str = "Majority class",
    xlabel: str | None = None,
) -> Figure:
    """Per-fold scores of each model, best mean on top. Highlighted models are drawn in
    ink (and bold), the rest muted; `reference` adds a dashed chance-level line."""
    order = folds.groupby(model_col)[metric].mean().sort_values(ascending=False).index
    marked = {highlight} if isinstance(highlight, str) else set(highlight or ())
    colors = {m: INK if m in marked or not marked else INK_MUTED for m in order}
    fig, ax = plt.subplots(figsize=(FULL_WIDTH, 0.32 * len(order) + 0.8))
    strip_box(ax, {m: folds.loc[folds[model_col] == m, metric] for m in order}, colors, point_size=7, jitter=0.16)
    for t in ax.get_yticklabels():
        if t.get_text() in marked:
            t.set_fontweight("bold")
            t.set_color(INK)
    if reference is not None:
        ax.axvline(reference, color=INK_SECONDARY, linestyle="--", linewidth=0.9, zorder=2)
        ax.annotate(reference_label, (reference, 1), xycoords=("data", "axes fraction"), xytext=(3, 2),
                    textcoords="offset points", fontsize=BASE_FONT_SIZE - 1.5, color=INK_SECONDARY, va="bottom")
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlabel(xlabel or {"accuracy": "Accuracy", "macro_f1": "Macro F1"}.get(metric, metric))
    return fig


def confusion_frame(true: Sequence[str], pred: Sequence[str], labels: Sequence[str] = STYLES) -> pd.DataFrame:
    """Confusion counts as a labeled frame: rows are true classes, columns predicted."""
    names = [str(s) for s in labels]
    return pd.DataFrame(confusion_matrix(true, pred, labels=names), index=names, columns=names)


def confusion_matrices(matrices: pd.DataFrame | Mapping[str, pd.DataFrame], *, ncols: int = 3) -> Figure:
    """Row-normalized confusion matrices (share of each true class predicted as each class).
    Pass one frame from `confusion_frame`, or {title: frame} for small multiples."""
    items = {"": matrices} if isinstance(matrices, pd.DataFrame) else dict(matrices)
    ncols = min(ncols, len(items))
    nrows = ceil(len(items) / ncols)
    side = min(2.4, (FULL_WIDTH - 0.6) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(side * ncols + 0.6, side * nrows + 0.3), squeeze=False,
                             sharex=True, sharey=True)
    for ax, (title, cm) in zip(axes.flat, items.items()):
        shares = cm.div(cm.sum(axis=1).replace(0, np.nan), axis=0)
        _heat(ax, shares, SEQUENTIAL, Normalize(0, 1), "{:.0%}", BASE_FONT_SIZE - 1.5)
        ax.set_title(title)
        _rotate_xticklabels(ax, 30)
    for ax in axes.flat[len(items):]:
        ax.set_visible(False)
    fig.supylabel("True style", color=INK_SECONDARY)
    fig.supxlabel("Predicted style", color=INK_SECONDARY)
    return fig


def importance_plot(
    mean: pd.Series,
    error: pd.Series | None = None,
    ax: Axes | None = None,
    *,
    xlabel: str = "Drop in accuracy when shuffled",
) -> Figure:
    """Dot-and-whisker chart of per-feature scores (e.g. permutation importance with its
    spread across folds), largest on top, with a zero reference line."""
    order = mean.sort_values().index
    ax = _new_axes(ax, figsize("half", 0.25 * len(order) / HALF_WIDTH + 0.3))
    y = np.arange(len(order))
    ax.errorbar(mean[order], y, xerr=None if error is None else error[order], fmt="o", color=INK,
                ecolor=INK_MUTED, elinewidth=1.0, capsize=0, markersize=4.5)
    ax.axvline(0, color=AXIS, linewidth=0.8, zorder=1)
    ax.set_yticks(y, [label(i) for i in order])
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel(xlabel)
    return ax.figure


# -- affinity, mixes and adjustment -----------------------------------------


def style_mix(mixes: pd.DataFrame, ax: Axes | None = None) -> Figure:
    """100% stacked bars: one row per index entry (top to bottom), split into the style
    shares in its columns; the static counterpart of the app's style-mix chart."""
    shares = mixes.div(mixes.sum(axis=1), axis=0)
    styles = [str(s) for s in STYLES if str(s) in shares.columns]
    ax = _new_axes(ax, (FULL_WIDTH, 0.36 * len(shares) + 0.75))
    y = np.arange(len(shares))[::-1]
    left = np.zeros(len(shares))
    for s in styles:
        w = shares[s].to_numpy()
        ax.barh(y, w, left=left, height=0.62, color=style_color(s), edgecolor=SURFACE, linewidth=1.5, label=label(s))
        for yi, li, wi in zip(y, left, w):
            if wi >= MIN_LABELED_SHARE:
                ax.text(li + wi / 2, yi, f"{wi:.0%}", ha="center", va="center", fontsize=BASE_FONT_SIZE - 1.5,
                        color=INK, fontweight="bold")
        left += w
    ax.set_yticks(y, [label(i) for i in shares.index])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.tick_params(axis="y", length=0)
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    _top_legend(ax, _style_handles(styles, marker="s"))
    return ax.figure


def before_after(
    pairs: Mapping[str, tuple[pd.Series, pd.Series]],
    *,
    xlabel: str = "Distance before",
    ylabel: str = "Distance after",
    title: Callable[[str], str] = lambda k: f"Toward {label(k)}",
) -> Figure:
    """Small multiples of before vs after (e.g. distance to the target centroid), one panel
    per key, with the y = x line; points below it improved. Style keys take the style color."""
    keys = list(pairs)
    hi = max(max(b.max(), a.max()) for b, a in pairs.values()) * 1.05
    fig, axes = plt.subplots(1, len(keys), figsize=(FULL_WIDTH, FULL_WIDTH / len(keys) + 0.45),
                             sharex=True, sharey=True, squeeze=False)
    for ax, k in zip(axes.flat, keys):
        before, after = pairs[k]
        ax.plot([0, hi], [0, hi], color=INK_MUTED, linestyle="--", linewidth=0.9, zorder=1)
        ax.scatter(before, after, s=10, color=style_color(k) if _is_style(k) else INK_SECONDARY,
                   edgecolor=SURFACE, linewidth=0.4, alpha=0.85, zorder=3)
        ax.text(0.97, 0.04, f"{(after < before).mean():.0%} closer", transform=ax.transAxes, ha="right",
                fontsize=BASE_FONT_SIZE - 1.5, color=INK_SECONDARY)
        ax.set(xlim=(0, hi), ylim=(0, hi), aspect="equal", title=title(k))
        ax.grid(axis="both", visible=True)
    fig.supxlabel(xlabel, color=INK_SECONDARY)
    fig.supylabel(ylabel, color=INK_SECONDARY)
    return fig


_TRIANGLE: Final = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, np.sqrt(3) / 2]])  # STYLES corners


def _simplex_xy(shares: pd.DataFrame) -> np.ndarray:
    w = shares[[str(s) for s in STYLES]].to_numpy(dtype=float)
    return (w / w.sum(axis=1, keepdims=True)) @ _TRIANGLE


def _simplex_frame(ax: Axes, step: float | None = 0.2) -> None:
    """Triangle with each style at its corner (labeled, with its color), optional share gridlines."""
    if step:
        for k in range(3):  # lines where style k's share is constant
            a, b = (j for j in range(3) if j != k)
            for t in np.arange(step, 1 - 1e-9, step):
                p, q = t * _TRIANGLE[k] + (1 - t) * _TRIANGLE[a], t * _TRIANGLE[k] + (1 - t) * _TRIANGLE[b]
                ax.plot([p[0], q[0]], [p[1], q[1]], color=GRID, linewidth=0.6, zorder=1)
    ax.add_patch(plt.Polygon(_TRIANGLE, closed=True, fill=False, edgecolor=AXIS, linewidth=0.9, zorder=2))
    for s, (x, y) in zip(STYLES, _TRIANGLE):
        top = y > 0
        ax.annotate(label(s), (x, y), xytext=(0, 9 if top else -9), textcoords="offset points",
                    ha="center", va="bottom" if top else "top", fontweight="bold", zorder=6)
    ax.set_aspect("equal")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.12, np.sqrt(3) / 2 + 0.1)
    ax.axis("off")


def ternary(
    achieved: pd.DataFrame,
    requested: pd.DataFrame | None = None,
    ax: Axes | None = None,
    *,
    step: float = 0.2,
) -> Figure:
    """Style mixes on the three-style simplex: each corner is a pure style, the center an
    even blend. With `requested` (same index), each achieved mix is joined to the mix that
    was asked for, so the gap is the adjuster's error."""
    ax = _new_axes(ax, figsize("half", 0.95))
    _simplex_frame(ax, step)
    for s, (x, y) in zip(STYLES, _TRIANGLE):
        ax.scatter([x], [y], s=40, color=style_color(s), edgecolor=SURFACE, linewidth=0.8, zorder=5, clip_on=False)
    got = _simplex_xy(achieved)
    handles = [Line2D([], [], marker="o", linestyle="", markersize=5, color=INK, label="Achieved")]
    if requested is not None:
        asked = _simplex_xy(requested.loc[achieved.index])
        for (x0, y0), (x1, y1) in zip(asked, got):
            ax.plot([x0, x1], [y0, y1], color=INK_MUTED, linewidth=0.7, zorder=3)
        ax.scatter(*asked.T, s=22, facecolor=SURFACE, edgecolor=INK_SECONDARY, linewidth=1.0, zorder=4)
        handles.insert(0, Line2D([], [], marker="o", linestyle="", markersize=5, markerfacecolor=SURFACE,
                                 markeredgecolor=INK_SECONDARY, label="Requested"))
    ax.scatter(*got.T, s=14, color=INK, edgecolor=SURFACE, linewidth=0.4, zorder=4)
    ax.legend(handles=handles, loc="upper left", frameon=False)
    return ax.figure


def recipe_network(
    G: nx.Graph,
    kind: Literal["centroid", "neighbor"] = "centroid",
    ax: Axes | None = None,
    *,
    seed: int = 0,
) -> Figure:
    """Draw a graph from `build_graph`.

    kind="centroid": each style centroid sits at a corner of a triangle and each recipe at
    the affinity-weighted average of the corners, so its position reads as its affinity
    scores and its edges (width = affinity) show the pull of each style. kind="neighbor":
    recipes only, joined to their nearest recipes by a force layout; dashed ink edges cross
    styles and mark where styles blur together.
    """
    recipes = [n for n, d in G.nodes(data=True) if d["kind"] == "recipe"]
    groups = _ordered_groups(pd.Series([G.nodes[n]["style"] for n in recipes]))
    handles = _style_handles(groups)
    if kind == "centroid":
        ax = _new_axes(ax, figsize("full", 0.78))
        _simplex_frame(ax, step=None)
        corners = {str(s): xy for s, xy in zip(STYLES, _TRIANGLE)}
        pos = {s: corners[s] for s in corners}
        for n in recipes:
            aff = np.array([G.edges[n, s]["affinity"] for s in corners])
            pos[n] = aff / aff.sum() @ np.array(list(corners.values()))
        H = G.edge_subgraph([(u, v) for u, v, d in G.edges(data=True) if d["kind"] == "centroid"])
        nx.draw_networkx_edges(H, pos, ax=ax, edge_color=AXIS, alpha=0.5,
                               width=[0.1 + 1.6 * H.edges[e]["affinity"] for e in H.edges])
        nx.draw_networkx_nodes(H, pos, nodelist=list(corners), ax=ax, node_shape="D", node_size=110,
                               node_color=[style_color(s) for s in corners], edgecolors=INK, linewidths=1.1)
        handles.append(Line2D([], [], marker="D", linestyle="", markersize=7, markerfacecolor=SURFACE,
                              markeredgecolor=INK, label="Style centroid"))
    else:
        ax = _new_axes(ax, figsize("full", 0.72))
        H = G.subgraph(recipes).edge_subgraph(
            [(u, v) for u, v, d in G.subgraph(recipes).edges(data=True) if d["kind"] == "neighbor"]
        )
        H = nx.compose(nx.empty_graph(recipes), H)  # keep isolated recipes
        pos = nx.spring_layout(H, seed=seed)
        same = [(u, v) for u, v, d in H.edges(data=True) if d["same_style"]]
        cross = [(u, v) for u, v, d in H.edges(data=True) if not d["same_style"]]
        nx.draw_networkx_edges(H, pos, edgelist=same, ax=ax, edge_color=AXIS, width=0.8)
        nx.draw_networkx_edges(H, pos, edgelist=cross, ax=ax, edge_color=INK, width=0.9, style="dashed")
        handles.append(Line2D([], [], color=INK, linestyle="--", linewidth=0.9, label="Cross-style neighbor"))
    nx.draw_networkx_nodes(H, pos, nodelist=recipes, ax=ax, node_size=22, linewidths=0.5, edgecolors=SURFACE,
                           node_color=[style_color(G.nodes[n]["style"]) for n in recipes])
    ax.axis("off")
    _top_legend(ax, handles)
    return ax.figure

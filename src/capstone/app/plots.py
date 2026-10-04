"""Plots used by the Streamlit app."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class RadarSeries:
    values: Sequence[float]  # one value in [0, 1] per axis
    color: str
    filled: bool = True


def triangle_radar(axes: Sequence[str], series: Mapping[str, RadarSeries]) -> plt.Figure:
    """Radar chart with straight-edged (polygonal) gridlines, one spoke per axis.

    Args:
        axes: Axis labels, e.g. the three styles.
        series: Label -> values to draw; unfilled series are dashed (e.g. a target).
    """
    angles = np.pi / 2 + np.arange(len(axes)) * 2 * np.pi / len(axes)
    spokes = np.c_[np.cos(angles), np.sin(angles)]
    fig, ax = plt.subplots(figsize=(5, 5))
    for level in (0.25, 0.5, 0.75, 1.0):
        ring = np.vstack([spokes * level, spokes[:1] * level])
        ax.plot(*ring.T, color="lightgray", lw=0.8 if level < 1 else 1.2, zorder=0)
        ax.text(*(spokes[0] * level + [0.03, 0]), f"{int(level * 100)}%", fontsize=7, color="gray", va="center")
    for spoke in spokes:
        ax.plot([0, spoke[0]], [0, spoke[1]], color="lightgray", lw=0.8, zorder=0)
    for label, spoke in zip(axes, spokes):
        ax.text(*(spoke * 1.12), label, ha="center", va="center", fontsize=10)
    for label, s in series.items():
        pts = spokes * np.asarray(s.values)[:, None]
        closed = np.vstack([pts, pts[:1]])
        ax.plot(*closed.T, color=s.color, ls="-" if s.filled else "--", lw=2, label=label)
        if s.filled:
            ax.fill(*closed.T, color=s.color, alpha=0.15)
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-0.7, 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    return fig

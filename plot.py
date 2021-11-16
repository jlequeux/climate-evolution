import altair as alt
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from matplotlib.colors import ListedColormap

DIVERGING_CMAPS = [
    'PiYG',
    'PRGn',
    'BrBG',
    'PuOr',
    'RdGy',
    'RdBu',
    'RdYlBu',
    'RdYlGn',
    'Spectral',
    'coolwarm',
    'bwr',
    'seismic',
]


def create_qualitative_from_linear(cmap_name, size):
    """Generate a qualitative custom cmap from a linear one"""
    cmap = cm.get_cmap(cmap_name, int(256 / size) * size)
    a = np.linspace(0, 1, size)
    a = np.tile(a, (int(256 / size), 1)).flatten()
    a.sort()
    return ListedColormap(cmap(a))


def color_map(ds, label, cmap):
    """Plot a map with coastline from an xarray"""
    subplot_kws = dict(projection=ccrs.Robinson(), facecolor='grey')

    p = ds.plot(
        transform=ccrs.PlateCarree(),
        cmap=cmap,
        subplot_kws=subplot_kws,
        add_colorbar=False,
        vmin=min(-ds.max(), ds.min()).values,  # fix cases when min > 0
    )
    p.axes.coastlines()
    p.axes.gridlines(color='black', alpha=0.5, linestyle='--')
    p.figure.patch.set_alpha(0)

    fg_color = 'white'
    cbar = p.figure.colorbar(p, orientation="horizontal", pad=0.2)
    cbar.set_label(label, color=fg_color)
    cbar.ax.xaxis.set_tick_params(color=fg_color)
    plt.setp(plt.getp(cbar.ax.axes, 'xticklabels'), color=fg_color)
    return p


def line(df, variable, x='time', color_var='variable'):
    """Line plot + trend of a dataframe variable using altair"""
    p = (
        alt.Chart(df)
        .mark_line()
        .encode(
            alt.Y(variable, scale=alt.Scale(zero=False)),
            x=x,
        )
    )
    trend = p.transform_regression(x, variable).mark_line(strokeDash=[2, 1], color='steerblue')
    p = p.encode(
        color=alt.Color(
            color_var,
            scale=alt.Scale(
                scheme='set2',
            ),
        ),
        tooltip=[x, variable],
    )
    chart = (trend + p).interactive().properties(width=800)
    return chart

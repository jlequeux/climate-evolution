import geopy
import intake
import numpy as np
import pandas as pd
import streamlit as st
from geopy.geocoders import Nominatim

import paths
import plot

GEOLOCATOR = Nominatim(user_agent="climate-evolution")


def get_location(query: str):
    """Get location information from string"""
    if not query:
        return False
    try:
        return GEOLOCATOR.geocode(query)
    except geopy.exc.GeocoderServiceError as e:
        st.text(f'Error in geocoding: {e}')
        return False


def climate_evolution_per_location():
    """Show variable evolution for a location"""
    catalog = intake.open_catalog(paths.ECMWF_CMIP6_CATALOG)
    variable = st.selectbox('Variable', list(catalog))

    query = st.text_input('Enter you city or country')
    location = get_location(query)
    if not location:
        return
    st.text(f"showing data for {location.address}")

    ds = catalog[variable].read()
    rolling = st.slider('Rolling window (years)', min_value=1, max_value=10)
    scenarios = st.multiselect('Scenarios', list(ds.data_vars), list(ds.data_vars))

    ds = (
        ds.sel(latitude=location.latitude, longitude=location.longitude, method="nearest")
        .rolling(time=rolling)
        .mean()
    )
    df = ds.to_dataframe()[scenarios]
    column_name = 'scenarios'
    df = df.stack().to_frame(variable).reset_index().rename(columns={'level_1': column_name})
    df = df.sort_values('time', ascending=True)

    year_min, year_max = df.time.min().year, df.time.max().year
    start, end = st.slider('Date range:', year_min, year_max, (year_min, year_max))
    df = df.where(
        (df.time.dt.year >= start) & (df.time.dt.year <= end)
    ).dropna()

    st.altair_chart(plot.line(df, variable, color_var=column_name))

    st.write(
        'More details on SSP scenarios: https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways'
    )


def get_years_range(ds):
    ds = ds.dropna('time')
    _min = pd.to_datetime(ds.time.min().values).year
    _max = pd.to_datetime(ds.time.max().values).year
    return (_min, _max)


def spatial_anomalies():
    """Show temperature anomalies between 2 dates"""

    catalog = intake.open_catalog(paths.ECMWF_CMIP6_CATALOG)
    variable = st.selectbox('Variable', list(catalog))
    ds = catalog[variable].read()

    scenario = st.selectbox('Scenario', list(ds.data_vars), 1)
    col1, col2 = st.columns(2)
    reference_year = col1.slider(
        'Reference date (historical data)', *get_years_range(ds['historical'])
    )
    comparison_year = col2.slider(
        'Comparison date (data from selected Scenario)', *get_years_range(ds[scenario])
    )

    with st.expander("Spatial selection"):
        query = st.text_input('Enter you city or country')
        location = get_location(query)

        if not location:
            st.write('or select lat/lon manually')
            col3, col4 = st.columns(2)
            min_max_lats = (ds.latitude.min().item(), ds.latitude.max().item())
            min_max_lons = (ds.longitude.min().item(), ds.longitude.max().item())
            latitudes = col3.slider('Latitudes', *min_max_lats, min_max_lats)
            longitudes = col4.slider('Longitudes', *min_max_lons, min_max_lons)
        else:
            lat_s, lat_n, lon_w, lon_e = [float(x) for x in location.raw['boundingbox']]
            lat_resolution = np.round(ds.latitude[1] - ds.latitude[0], 3)
            lon_resolution = np.round(ds.longitude[1] - ds.longitude[0], 3)
            if (lat_n - lat_s) < lat_resolution or (lon_e - lon_w) < lon_resolution:
                st.error(f'Area "{location.address}" is too small')
                return
            latitudes = (lat_s, lat_n)
            longitudes = (lon_w, lon_e)

    reference_map = (
        ds['historical']
        .sel(time=pd.to_datetime(f'{reference_year}-12-31'), method='ffill')
        .sel(latitude=slice(*latitudes), longitude=slice(*longitudes))
    )
    comparison_map = (
        ds[scenario]
        .sel(time=pd.to_datetime(f'{comparison_year}-12-31'), method='backfill')
        .sel(latitude=slice(*latitudes), longitude=slice(*longitudes))
    )

    with st.expander("Color settings"):
        sign = -1 if st.checkbox('Reverse difference') else 1
        colormap = st.selectbox('Colormap', plot.DIVERGING_CMAPS, 9)

    st.subheader(f'Showing anomalies between {reference_year} and {comparison_year}')

    anomaly_map = (sign * comparison_map) - (sign * reference_map)
    qualitative_coolwarm = plot.create_qualitative_from_linear(colormap, 12)
    p = plot.color_map(
        anomaly_map,
        label=variable,
        cmap=qualitative_coolwarm,
    )
    st.pyplot(p.figure)


OPTIONS = {
    'Climate evolution at your location': climate_evolution_per_location,
    'Map of anomalies': spatial_anomalies,
}


if __name__ == '__main__':
    service = st.sidebar.selectbox('What do you want to see?', list(OPTIONS.keys()))
    st.title(service)
    OPTIONS[service]()

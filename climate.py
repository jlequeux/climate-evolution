import datetime

import geopy
import intake
import pandas as pd
import streamlit as st
import xarray as xr
from geopy.geocoders import Nominatim

import paths
import plot

GEOLOCATOR = Nominatim(user_agent="climate-evolution")


# VARIABLES = ['temperature', 'precipitation']
YEAR_NOW = datetime.datetime.now().year
# RCPs = ['4.5', '8.5']


def get_location(query):
    if not query:
        return False
    try:
        return GEOLOCATOR.geocode(query)
    except geopy.exc.GeocoderServiceError as e:
        st.text(f'Error in geocoding: {e}')
        return False


def climate_evolution_per_location():
    """Show temperature evolution for a location"""
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

    _min = df.time.min().year
    _max = df.time.max().year
    date_range = st.slider('Date range:', _min, _max, (_min, _max))
    df = df.where(
        (df.time >= pd.to_datetime(date_range[0], format='%Y'))
        & (df.time <= pd.to_datetime(date_range[1], format='%Y'))
    ).dropna()

    st.altair_chart(plot.line(df, variable, color_var=column_name))

    st.write(
        'More details on SSP scenarios: https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways'
    )


def temperature_anomalies():
    """Show temperature anomalies between 2 dates"""

    # TODO(jeremie): add spatial selection
    catalog = intake.open_catalog(paths.CLIMATE_CATALOG)
    historical_temperatures = catalog['historical'].read()

    st.text('Show temperature anomalies between:')

    hist_last_year_idx = len(historical_temperatures.year.values) - 1
    reference_year = st.selectbox(
        'Historical data from: ',
        historical_temperatures.year.values,
        index=hist_last_year_idx,
    )

    rcp_model = st.selectbox('RCP model', RCPs)
    prediction_data = catalog[f'prediction RCP {rcp_model}'].read()
    pred_last_year_idx = len(prediction_data.year.values) - 1
    comparison_year = st.selectbox(
        'Predictions from: ', prediction_data.year.values, index=pred_last_year_idx
    )

    reference_tmp_map = historical_temperatures.sel(year=reference_year, method='nearest')
    # st.write(reference_tmp_map.year)
    comparison_tmp_map = prediction_data.sel(year=comparison_year, method='nearest')
    # st.write(comparison_tmp_map.year)
    sign = -1 if st.checkbox('Reverse difference') else 1
    anomaly_map = (sign * comparison_tmp_map) - (sign * reference_tmp_map)

    qualitative_coolwarm = plot.create_qualitative_from_linear('coolwarm', 12)
    p = plot.color_map(
        anomaly_map['temperature'],
        label="Temperature anomalies(°C)",
        cmap=qualitative_coolwarm,
    )

    st.pyplot(p.figure)


OPTIONS = {
    'Temperature evolution at your location': climate_evolution_per_location,
    'Map of temperature anomalies': temperature_anomalies,
}


if __name__ == '__main__':
    service = st.sidebar.selectbox('What do you want to see?', list(OPTIONS.keys()))
    st.title(service)
    OPTIONS[service]()

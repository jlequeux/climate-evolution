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


VARIABLES = ['temperature', 'precipitation']
YEAR_NOW = datetime.datetime.now().year
RCPs = ['4.5', '8.5']


def get_dataset():
    """Get and concatenate datasets from the catalog"""
    catalog = intake.open_catalog(paths.CLIMATE_CATALOG)
    arrays = []
    arrays.append(catalog['historical'].read())
    _ = [arrays.append(catalog[f'prediction RCP {rcp}'].read()) for rcp in RCPs]
    return xr.concat(arrays, 'RCP')


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
    # TODO(jeremie): add other variables
    variable = 'temperature'

    query = st.text_input('Enter you city or country')
    location = get_location(query)
    if not location:
        return

    st.text(f"showing {variable} for {location.address}")
    rolling = st.slider('Rolling window (years)', min_value=1, max_value=10)

    ds_location = (
        get_dataset()
        .sel(latitude=location.latitude, longitude=location.longitude, method="nearest")
        .rolling(year=rolling)
        .mean()
    )
    df = ds_location.to_dataframe().reset_index()

    df.loc[df['RCP'] == '0', 'type'] = 'historical'
    for rcp in RCPs:
        df.loc[df['RCP'] == rcp, 'type'] = f'prediction - RCP {rcp}'

    df = df.dropna()
    df['year'] = pd.to_datetime(df['year'], format='%Y')
    df = df.sort_values('year', ascending=True)

    st.altair_chart(plot.line(df, variable))

    tmp_past = df.iloc[0][variable]
    year_past = df.iloc[0]['year']
    tmp_now = df.query('RCP == "0"').iloc[-1][variable]
    year_now = df.query('RCP == "0"').iloc[-1]['year']
    difference_now = tmp_now - tmp_past
    st.text(
        f'In {year_now.year} the {variable} is {difference_now:.02f}°C'
        f' {"higher" if difference_now > 0 else "lower"} than in {year_past.year}'
    )

    for rcp in RCPs:
        tmp_futur = df.query(f'RCP == "{rcp}"').iloc[-1][variable]
        year_futur = df.query(f'RCP == "{rcp}"').iloc[-1]['year']
        difference_futur = tmp_futur - tmp_now
        st.text(
            f'With scenario RCP {rcp}: '
            f'in {year_futur.year} the {variable} will be {difference_futur:.02f}°C'
            f' {"higher" if difference_futur > 0 else "lower"} compared to {year_now.year}'
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

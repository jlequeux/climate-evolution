import streamlit as st

import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import numpy as np
from geopy.geocoders import Nominatim
import altair as alt
import cartopy.crs as ccrs

GEOLOCATOR = Nominatim(user_agent="climate-evolution")    

DATA_FOLDER = 'data'
YEAR_NOW = datetime.datetime.now().year


# @st.cache
def get_yearly_temperature():
    ds = xr.open_dataset(f'{DATA_FOLDER}/temperature_monthly-mean_ipsl-cm5a-lr_rcp45_r1i1p1_1950-2100_v1.0.nc')
    ds = ds.rename_vars({'temperature_monthly-mean': 'temperature'})
    ds['temperature'] = ds['temperature'] - 273.15
    return ds.groupby('time.year').mean()['temperature']
    

def temperature_evolution_per_location():
    city = st.text_input('Enter you city')
    if not city:
        return
    location = GEOLOCATOR.geocode(city)
    st.text(f"showing temperature for {location.address}")
    rolling = st.slider('Rolling window (years)', min_value=1, max_value=10)

    yearly_temperature = get_yearly_temperature()
    ds_location = (
        yearly_temperature
        .sel(latitude=location.latitude, longitude=location.longitude, method="nearest")
        .rolling(year=rolling).mean()
    )
    df = ds_location.to_dataframe().reset_index()

    df.loc[df['year'] <= YEAR_NOW,'type'] = 'historical'
    df.loc[df['year'] > YEAR_NOW,'type'] = 'predictions'
    df = df[['year', 'temperature', 'type']].dropna()
    df['year'] = pd.to_datetime(df['year'], format='%Y')
    df = df.sort_values('year', ascending=True)

    p = (
        alt.Chart(df)
        .mark_line()
        .encode(
            alt.Y('temperature', scale=alt.Scale(zero=False)),
            x='year',)
    )
    trend = p.transform_regression('year', 'temperature').mark_line(strokeDash=[2,1], color='steerblue')
    p = p.encode(
        color=alt.Color('type', 
            scale=alt.Scale(
                scheme='set2',
                #domain=['historical', 'predictions'], range=['steerblue', 'peachpuff']
                )
            ), 
        tooltip=['year', 'temperature'])
    chart = (
        (trend + p)
        .interactive()
        .properties(width=800)
    )
    
    st.altair_chart(chart)

    tmp_past = df.iloc[0]['temperature']
    year_past = df.iloc[0]['year']
    tmp_now = df.loc[df['year'] <= f'{YEAR_NOW}-01-01'].iloc[-1]['temperature']
    year_now = df.loc[df['year'] <= f'{YEAR_NOW}-01-01'].iloc[-1]['year']
    tmp_futur = df.iloc[-1]['temperature']
    year_futur = df.iloc[-1]['year']
    difference_now = tmp_now - tmp_past
    difference_futur = tmp_futur - tmp_now

    st.text(f'In {year_now.year} the temperature is {difference_now:.02f}°C {"higher" if difference_now > 0 else "lower"} than in {year_past.year}')
    st.text(f'In {year_futur.year} the temperature will be {difference_futur:.02f}°C {"higher" if difference_futur > 0 else "lower"} than in {year_now.year}')
    st.text(f'Total difference from {year_past.year} to {year_futur.year}: {difference_now+difference_futur:.02f}°C')


def temperature_anomalies():
    yearly_temperature = get_yearly_temperature()
    st.text('Show temperature anomalies between:')
    year_now_index = int(np.where(yearly_temperature.year==YEAR_NOW)[0])
    reference_year = st.selectbox('Reference date: ', yearly_temperature.year.values, index=year_now_index)
    comparison_year = st.selectbox('Anomalies with: ', yearly_temperature.year.values)
    
    reference_tmp_map = yearly_temperature.sel(year=reference_year, method='nearest')
    comparison_tmp_map = yearly_temperature.sel(year=comparison_year, method='nearest')
    anomaly_map = reference_tmp_map - comparison_tmp_map

    p = anomaly_map.plot(subplot_kws={'projection': ccrs.PlateCarree()}, add_colorbar=False)
    p.axes.coastlines()
    p.figure.patch.set_alpha(0)

    fg_color = 'white'
    cbar = p.figure.colorbar(p, orientation="horizontal", pad=0.2)
    cbar.set_label("Temperature anomalies(°C)")
    cbar.set_label("Temperature anomalies(°C)", color=fg_color)
    cbar.ax.xaxis.set_tick_params(color=fg_color)
    plt.setp(plt.getp(cbar.ax.axes, 'xticklabels'), color=fg_color)
    # cbar.outline.set_edgecolor(fg_color)
    
    st.pyplot(p.figure)
    


OPTIONS = {'Temperature evolution at your location': temperature_evolution_per_location,
           'Temperature Anomalies': temperature_anomalies}


if __name__ == '__main__':
    service = st.sidebar.selectbox('What do you want to see?', OPTIONS.keys())
    st.title(service)
    OPTIONS[service]()

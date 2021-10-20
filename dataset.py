"""Dataset and calalogs management"""
from loguru import logger
import datetime
import intake
import pandas as pd
import os
import yaml

import paths

NOW = pd.to_datetime(f'{datetime.datetime.now().year}-01-01')
OLDEST_DATE = pd.to_datetime('1950-01-01')
FURTHER_DATE = pd.to_datetime('2100-12-01')


def build_yearly_temperature_entry(start_date, end_date, name, rcp):
    """Build and cut dataset between start_date and end_date for a particular RCP
    convert to Celcius, save it to zarr and return the catalog entry as a string"""
    catalog = intake.open_catalog(paths.ECMWF_CATALOG)

    query_rcp = rcp
    if rcp == '0':
        query_rcp = '4.5'  # get 4.5 by default for historical data - both historical data are the same

    ecmwf_ds = catalog[f'ecmwf_temperature_rcp{query_rcp}'].read()
    ds = ecmwf_ds.where(
        (ecmwf_ds.time > start_date) & (ecmwf_ds.time < end_date), drop=True
    )

    ds = ds.rename_vars({'temperature_monthly-mean': 'temperature'})
    ds['temperature'] = ds['temperature'] - 273.15
    ds = ds.assign_coords({'RCP': [rcp]})  # replace rcp for historical data

    ds = ds.groupby('time.year').mean()
    path = f'{paths.DATA_FOLDER}/temperature_{rcp}_{start_date:%Y%d%m}_{end_date:%Y%d%m}.zarr'
    ds.to_zarr(path, mode='w')
    logger.info(f'dataset {path} saved')

    content = intake.open_zarr(path)
    content.name = name
    content.description = (
        f'{name} temperature from {start_date:%Y%d%m} to {end_date:%Y%d%m}'
    )

    return yaml.safe_load(content.yaml())['sources']


def create_catalog(entries, filename):
    catalog_content = {'sources': entries}
    with open(filename, 'w') as file:
        yaml.dump(catalog_content, file)


def build_climate_catalog(filename=paths.CLIMATE_CATALOG):
    """Create a catalog file"""
    if os.path.exists(paths.CLIMATE_CATALOG):
        logger.info(f'Existing Catalog: {filename}, continue without building.')
        return
    catalog_content = {}
    catalog_content.update(
        build_yearly_temperature_entry(OLDEST_DATE, NOW, 'historical', '0')
    )
    for rcp in ['4.5', '8.5']:
        catalog_content.update(
            build_yearly_temperature_entry(
                NOW, FURTHER_DATE, f'prediction RCP {rcp}', rcp
            )
        )

    create_catalog(catalog_content, filename)
    logger.info(f'Catalog {filename} created')


if __name__ == '__main__':
    build_climate_catalog()

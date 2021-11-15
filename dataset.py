"""Dataset and calalogs management"""
import datetime
import os

import cdsapi
import intake
import pandas as pd
import pathlib
import yaml
from loguru import logger
from decouple import config
from prefect import task, Flow
from typing import List, Tuple, Union, Dict
import zipfile
import xarray as xr

import paths

CDS_CLIENT = cdsapi.Client(url=config('CDSAPI_URL'), key=config('CDSAPI_KEY'), verify=True)


@task
def download_cmip6(
    experiment, temporal_resolution, level, variable, model, file_format='zip', force=False
) -> pathlib.PosixPath:
    """Request CMIP6 data from ECMWF and save it locally"""
    filename = f'{experiment}_{temporal_resolution}_{level}_{variable}_{model}.{file_format}'
    path = pathlib.Path(paths.DATA_FOLDER, file_format, filename)
    if path.exists() and not force:
        logger.info(f'Existing file: {path}')
        return path
    os.makedirs(path.parent, exist_ok=True)
    logger.info(f'Retrieving {filename}')
    CDS_CLIENT.retrieve(
        'projections-cmip6',
        {
            'format': file_format,
            'temporal_resolution': temporal_resolution,
            'experiment': experiment,
            'level': level,
            'variable': variable,
            'model': model,
        },
        path.as_posix(),
    )
    return path


@task
def extract_nc(path: Union[str, pathlib.PosixPath]) -> Tuple[pathlib.PosixPath]:
    """Extract .nc files from archive and save them"""
    extracted_files = []
    with zipfile.ZipFile(path, 'r') as zip_file:
        file_list = [pathlib.Path(f.filename) for f in zip_file.filelist]
        nc_files = list(filter(lambda x: x.suffix == '.nc', file_list))
        for file in nc_files:
            target_path = os.path.join(paths.DATA_FOLDER, 'nc')
            zip_file.extract(file.as_posix(), target_path)
            logger.info(f'File {file} extracted at {target_path} ')
            extracted_files.append(pathlib.Path(target_path, file.name))
    return tuple(extracted_files)


@task
def build_zarr(
    nc_paths: List[pathlib.PosixPath], name: str, resample: str = 'Y'
) -> pathlib.PosixPath:
    """Build and format a dataset from a list of nc files"""
    target_path = pathlib.Path(paths.DATA_FOLDER, 'zarr', f'{name}.zarr')
    if target_path.exists():
        logger.info(f'Existing zarr: {target_path}')
        return target_path

    def open_nc(path: pathlib.PosixPath, resample: str = 'Y') -> xr.Dataset:
        ds = xr.open_dataset(path)
        variable = ds.attrs['variable_id']
        experiment = ds.attrs['experiment_id']
        unit = ds[variable].attrs['units']

        da = ds[variable].rename(experiment)
        da = da.resample({'time': resample}).mean()

        if unit == 'K':
            da = da - 273.15

        return da

    ds = xr.merge([open_nc(nc_path) for nc_path in nc_paths])
    ds = ds.rename({'lat': 'latitude', 'lon': 'longitude'})
    ds = ds.assign_coords({'longitude': (ds.longitude + 180) % 360 - 180})  # convert to long3
    ds = ds.sortby('longitude')

    ds.to_zarr(target_path)
    ds.close()
    logger.info(f'Dataset {name} saved at {target_path}.')
    return target_path


@task
def entry_from_zarr(path: pathlib.PosixPath, name: str, description: str) -> dict:
    """Returns the yaml description for intake catalog for a given zarr file"""
    content = intake.open_zarr(path.as_posix())
    content.name = name
    content.description = description
    res = yaml.safe_load(content.yaml())['sources']
    return res


@task
def create_catalog(entries: list, filename: str) -> None:
    """Create intake catalog file"""
    content = {k: v for e in entries for (k, v) in e.items()}
    # TODO(jeremie): check if each entry is valid
    catalog_content = {'sources': content}
    logger.info(catalog_content)
    with open(filename, 'w') as file:
        yaml.dump(catalog_content, file)
    logger.info(f'Catalog created at {filename}')


def build_ecmwf_cmip6_catalog(path=paths.ECMWF_CMIP6_CATALOG):
    """Create ECMWF catalog file.
    Structure: 1 zarr per `experiment`, with several variables inside
    """

    experiments = ['historical', 'ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
    variables = [
        'near_surface_air_temperature'
    ]  # , 'sea_surface_height_above_geoid', 'precipitation']
    temporal_resolution = 'monthly'
    level = 'single_levels'
    model = 'cnrm_cm6_1_hr'
    resample = 'Y'

    catalog_entries = []
    for variable in variables:
        nc_paths = []
        for experiment in experiments:
            zip_path = download_cmip6(experiment, temporal_resolution, level, variable, model)
            nc_paths.extend(extract_nc(zip_path))

        zarr_name = (
            f'{temporal_resolution}_{resample}_{level}_{variable}_{model}_{"-".join(experiments)}'
        )
        description = f'ECMWF CMIP6 data: {zarr_name}'

        zarr_path = build_zarr(nc_paths, zarr_name, resample)
        catalog_entries.append(entry_from_zarr(zarr_path, variable, description))
    create_catalog(catalog_entries, path)


def open_dataset(experiment, catalog_path=paths.ECMWF_CMIP6_CATALOG):
    """Open a dataset from a catalog"""
    catalog = intake.open_catalog(catalog_path)
    return catalog[experiment].read()


if __name__ == '__main__':
    with Flow("building-catalogs") as flow:
        build_ecmwf_cmip6_catalog()
    flow.run()

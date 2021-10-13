"""Fixed paths to files or directories"""

import pathlib

ROOT = pathlib.Path(__file__).absolute().parent
DATA_FOLDER = f'{ROOT}/data'
CATALOG_FOLDER = f'{ROOT}/catalogs'
CLIMATE_CATALOG = f'{CATALOG_FOLDER}/climate_catalog.yaml'
ECMWF_CATALOG = f'{CATALOG_FOLDER}/ecmwf_catalog.yaml'

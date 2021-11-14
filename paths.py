"""Fixed paths to files or directories"""

import pathlib

ROOT = pathlib.Path(__file__).absolute().parent
DATA_FOLDER = f'{ROOT}/data'
CATALOG_FOLDER = f'{ROOT}/catalogs'
ECMWF_CMIP6_CATALOG = f'{CATALOG_FOLDER}/ecmwf_cmip6_catalog.yaml'

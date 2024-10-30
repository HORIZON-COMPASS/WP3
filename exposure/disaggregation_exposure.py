import pandas as pd
import numpy as np
import rasterio
import geopandas as gp
from rasterio.windows import Window
from exposure_functions import write_empty_raster, load_country_mask, load_dataset_by_country

## PARAMETERS
Harmonize = 'yes'
Last_hist_year = 2022 # last year of historical data
Compass_path = 'C:/HANZE2_products/Compass_exposure/'
Raster_path = 'C:/HANZE2_temp/'

# Define timespans
Years_all = list(range(1850,2101))
Years_hist = np.arange(1850,Last_hist_year+1).astype('str')
Years_hist_ssp = np.arange(1850,2021).astype('str')
Year_ssp_harm = list(range(Last_hist_year+1,2101))
Year_ssp_noharm = list(range(2021,2101))

# Load national exposure data (historical)
Pop_file = pd.read_csv(Compass_path + 'Pop_combined_SSP1_'+Harmonize+'.csv', index_col='ISOn')
GDP_file = pd.read_csv(Compass_path + 'GDP_combined_SSP1_'+Harmonize+'.csv', index_col='ISOn')
FA_file = pd.read_csv(Compass_path + 'FA_combined_SSP1_'+Harmonize+'.csv', index_col='ISOn')
Years_select = Years_hist if Harmonize == 'yes' else Years_hist_ssp
Pop_hist = Pop_file[Years_select]
GDP_hist = GDP_file[Years_select]
FA_hist = FA_file[Years_select]

# Load administrative map
country_dataset = rasterio.open(Compass_path + 'OSM_country_map.tif')
country_vector = gp.read_file('C:/HANZE2_rawdata/Admin/Global_OSM_boundaries_2024_v4.shp')

# test
ghsl_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')
hyde_dataset = rasterio.open(Raster_path + 'HYDE/zip/popc_1980AD.asc') # offset: left: 1 top: 108 right: 1 bottom: 198

# create disaggregation
dims = [country_dataset.height, country_dataset.width]
raster_profile = ghsl_dataset.profile
for year in Years_all:
    #write_empty_raster(year, raster_profile, Compass_path + 'Population_', np.float64, dims)

    for c in Pop_file.index:

        country_map = country_dataset.read(1, window=Window(43000, 10000, 1000, 1000))
        country_mask = country_map == c

        a=1


import pandas as pd
import numpy as np
import rasterio
import geopandas as gp
from exposure_functions import write_empty_raster, load_country_mask, load_dataset_by_country, save_raster_data

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
Year_ghsl = np.arange(1975,2035,5)

# Load national exposure data (historical)
Pop_data = dict()
GDP_data = dict()
FA_data = dict()
Years_select = Years_hist if Harmonize == 'yes' else Years_hist_ssp
for s in np.arange(0,5):
    Pop_data[s] = pd.read_csv(Compass_path + 'Pop_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    GDP_data[s] = pd.read_csv(Compass_path + 'GDP_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')
    FA_data[s] = pd.read_csv(Compass_path + 'FA_combined_SSP' + str(s + 1) + '_' + Harmonize + '.csv',
                              index_col='ISOn')

# Load administrative map
country_dataset = rasterio.open(Compass_path + 'OSM_country_map.tif')
country_vector = gp.read_file('C:/HANZE2_rawdata/Admin/Global_OSM_boundaries_2024_v4.shp')

# test
hyde_dataset = rasterio.open(Raster_path + 'HYDE/zip/popc_1980AD.asc') # offset: left: 1 top: 108 right: 1 bottom: 198

# create disaggregation
dims = [country_dataset.height, country_dataset.width]
for year in Years_all[125:181]:
    print(str(year))

    # Load GHSL data
    ghsl_pop_dataset_h = ''
    ghsl_bld_dataset_h = ''
    year_l = ''
    year_h = ''
    interp = 0
    if year > 1975:
        if year in Year_ghsl:
            ghsl_pop_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E'+str(year)+'_GLOBE_R2023A_4326_30ss_V1_0.tif')
            ghsl_bld_dataset = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E' + str(year) + '_GLOBE_R2023A_4326_30ss_V1_0.tif')
        else:
            # if year is between GHSL dataset, load upper and lower datasets for interpolation
            interp = 1
            year_l = max(Year_ghsl[Year_ghsl < year])
            year_h = min(Year_ghsl[Year_ghsl > year])
            ghsl_pop_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E'+str(year_l)+'_GLOBE_R2023A_4326_30ss_V1_0.tif')
            ghsl_bld_dataset = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E' + str(year_l) + '_GLOBE_R2023A_4326_30ss_V1_0.tif')
            ghsl_pop_dataset_h = rasterio.open(Raster_path + 'GHSL/GHS_POP_E'+str(year_h)+'_GLOBE_R2023A_4326_30ss_V1_0.tif')
            ghsl_bld_dataset_h = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E' + str(year_h) + '_GLOBE_R2023A_4326_30ss_V1_0.tif')
    else:
        # Use 1975 dataset for 1850-1974
        ghsl_pop_dataset = rasterio.open(Raster_path + 'GHSL/GHS_POP_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')
        ghsl_bld_dataset = rasterio.open(Raster_path + 'GHSL/GHS_BUILT_S_E1975_GLOBE_R2023A_4326_30ss_V1_0.tif')

    # write empty rasters for filling data
    Pop_raster = Compass_path + 'Population_' + str(year) + '.tif'
    # write_empty_raster(ghsl_pop_dataset.profile, Pop_raster, np.float64, dims)

    for c in Pop_data[1].index:

        print(Pop_data[1]['ISO3'][c])

        if Pop_data[1][str(year)][c] == 0:
            continue

        # Load data by country
        country_mask, location = load_country_mask(country_vector, c, country_dataset)
        location_ghsl = location + [0, 0, 0, 0]
        if interp == 1:
            ghsl_pop_year_l = load_dataset_by_country(ghsl_pop_dataset, location_ghsl, country_mask)
            ghsl_bld_year_l = load_dataset_by_country(ghsl_bld_dataset, location_ghsl, country_mask)
            ghsl_pop_year_h = load_dataset_by_country(ghsl_pop_dataset_h, location_ghsl, country_mask)
            ghsl_bld_year_h = load_dataset_by_country(ghsl_bld_dataset_h, location_ghsl, country_mask)
            ghsl_pop_year = ghsl_pop_year_l * (year_h - year) / 5 + ghsl_pop_year_h * (year - year_l) / 5
            ghsl_bld_year = ghsl_bld_year_l * (year_h - year) / 5 + ghsl_bld_year_h * (year - year_l) / 5
        else:
            ghsl_pop_year = load_dataset_by_country(ghsl_pop_dataset, location_ghsl, country_mask)
            ghsl_bld_year = load_dataset_by_country(ghsl_bld_dataset, location_ghsl, country_mask)

        ghsl_pop_year_total = ghsl_pop_year.sum()

        if year in Years_select:
            Pop_adjustment = Pop_data[1][str(year)][c] / ghsl_pop_year_total * 1000
            Pop_country_raster = ghsl_pop_year * Pop_adjustment
            # save_raster_data(Pop_raster, location_ghsl, country_mask, Pop_country_raster)
        else:
            for s in np.arange(0,5):
                Pop_adjustment = Pop_data[s][str(year)][c] / ghsl_pop_year_total * 1000
                Pop_country_raster = ghsl_pop_year * Pop_adjustment
                # save_raster_data(Pop_raster, location_ghsl, country_mask, Pop_country_raster)


        a=1


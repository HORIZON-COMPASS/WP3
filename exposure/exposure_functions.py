import numpy as np
import rasterio, os
from copulas.bivariate import Frank
from rasterio.windows import Window
from scipy.stats import rankdata, spearmanr

def prepare_fixed_asset_data(Fixed_asset_raw, GDPpc):

    Select_years = [3, 13, 23, 33, 43, 53, 66, 73, 82, 91, 103, 113, 123, 133, 143, 153, 163, 172]
    Fixed_asset_raw_a = Fixed_asset_raw.values[:, Select_years].astype(float)
    Fixed_asset_raw_av = Fixed_asset_raw_a.reshape(-1, 1)

    GDPpc_a = GDPpc.values[:, Select_years].astype(float)
    GDPpc_av = GDPpc_a.reshape(-1, 1)

    Combined_data = np.concatenate([GDPpc_av, Fixed_asset_raw_av], axis=1)
    Combined_data_d = Combined_data[~np.isnan(Combined_data).any(axis=1)]
    ix = (Combined_data_d > 0) & (Combined_data_d < 10)
    Combined_data_dz = Combined_data_d[ix.any(axis=1)]

    return Combined_data_dz

### Fit Frank copula to the data
def copula_fit_frank(Combined_data_dz):
    Combined_data_ranked = rankdata(Combined_data_dz, method='min', axis=0) / (Combined_data_dz.shape[0] + 1)
    copula = Frank()
    copula.fit(Combined_data_ranked)
    param = copula.theta
    X_margins = np.sort(np.stack([Combined_data_ranked[:, 0], Combined_data_dz[:, 0]], axis=1), axis=0)
    Y_margins = np.sort(np.stack([Combined_data_ranked[:, 1], Combined_data_dz[:, 1]], axis=1), axis=0)
    copula_assets = [param, X_margins, Y_margins]
    rng = np.random.default_rng(12345)
    copula_samples = rng.uniform(low=0, high=1, size=10000)

    return copula_assets, copula_samples

## Inference with Frank copula
def copula_inference_Frank(copula,u,v):

    theta = copula[0]
    X = copula[1]
    Y = copula[2]

    V = np.interp(v, X[:,1], X[:,0])

    a = -(1 / theta)
    b = 1 - np.exp( - theta)
    c = u ** -1 - 1
    d = np.exp( -theta * V)
    f = a * np.log( 1 - b / (c * d +1 ))
    f[f>1]=1
    sp = np.interp(f, Y[:,0], Y[:,1])

    return sp

def fixed_asset_estimate(Fixed_asset_orig, copula_assets, copula_samples, GDPpc_all, Years):

    Fixed_asset_raw = np.concatenate([Fixed_asset_orig,[np.nan] * (len(Years)-len(Fixed_asset_orig))])
    Fixed_asset_pred = np.zeros([len(Years)])
    Fixed_asset_pred_c = np.zeros([len(Years)])
    for y in Years:
        GDPpc_cy = GDPpc_all[y-1850]
        Fixed_asset_pred_c[y-1850] = np.mean(copula_inference_Frank(copula_assets, copula_samples, GDPpc_cy))
    asset_avail = ~np.isnan(Fixed_asset_raw.astype('float64'))
    if sum(asset_avail)==0:
        Fixed_asset_pred = Fixed_asset_pred_c
    else:
        Fixed_asset_pred[asset_avail] = Fixed_asset_raw[asset_avail]
        Index_first = np.where(asset_avail == 1)[0][0]
        Index_last = np.where(asset_avail == 1)[0][-1]
        Fixed_asset_first = Fixed_asset_raw[Index_first]
        Fixed_asset_last = Fixed_asset_raw[Index_last]
        Fixed_asset_pred[0:Index_first] = Fixed_asset_pred_c[0:Index_first] * Fixed_asset_first / Fixed_asset_pred_c[Index_first]
        Fixed_asset_pred[Index_last:] = Fixed_asset_pred_c[Index_last:] * Fixed_asset_last / Fixed_asset_pred_c[Index_last]

    Fixed_asset_pred[np.isnan(Fixed_asset_pred)] = 0

    return Fixed_asset_pred

def write_empty_raster(profile, full_filename, data_type, dimensions):

    mode = 'w'

    if os.path.isfile(full_filename):
        #os.remove(full_filename)
        print(full_filename + " already exists")
    else:
        empty_data = np.zeros(dimensions, dtype = data_type)
        with rasterio.Env():
            with rasterio.open(full_filename, mode, **profile) as dst:
                dst.write(empty_data, 1)

def load_country_mask(country_vector, c, country_dataset):

    country_vector_sel = country_vector.loc[country_vector['ISOnum']==c,]
    EXT_MIN_X = country_vector_sel['EXT_MIN_X'].values - country_dataset.bounds.left
    EXT_MAX_X = country_vector_sel['EXT_MAX_X'].values - country_dataset.bounds.left
    EXT_MIN_Y = country_vector_sel['EXT_MIN_Y'].values - country_dataset.bounds.bottom
    EXT_MAX_Y = country_vector_sel['EXT_MAX_Y'].values - country_dataset.bounds.bottom

    # find the country in the raster
    res = country_dataset.res[0]
    start_grid_x = np.floor(EXT_MIN_X / res)
    start_grid_y = np.floor(country_dataset.shape[0] - EXT_MAX_Y / res)
    extent_x = np.ceil((EXT_MAX_X - EXT_MIN_X) / res)
    extent_y = np.ceil((EXT_MAX_Y - EXT_MIN_Y) / res)
    location = np.concatenate([start_grid_x, start_grid_y, extent_x, extent_y])
    country = country_dataset.read(1, window=Window(start_grid_x, start_grid_y, extent_x, extent_y))
    # find grid cells specific for the country
    country_mask = country == c

    return country_mask, location

# helper for loading and masking raster for a NUTS region
def load_dataset_by_country(dataset, location, country_mask):

    col_off = location[0]
    row_off = location[1]
    width = location[2]
    height = location[3]

    read_dataset = dataset.read(1, window=Window(col_off, row_off, width, height))
    read_dataset[~country_mask] = 0
    read_dataset[read_dataset < 0] = 0

    return read_dataset

def save_raster_data(path_and_name, location, region_mask, raster_dataset):

    col_off = location[0]
    row_off = location[1]
    width = location[2]
    height = location[3]

    raster_dataset_year = rasterio.open(path_and_name)
    read_dataset_year = raster_dataset_year.read(1, window=Window(col_off, row_off, width, height))
    read_dataset_year[region_mask] = raster_dataset[region_mask]
    profile = raster_dataset_year.profile
    raster_dataset_year.close()
    with rasterio.open(path_and_name, 'r+', **profile) as dst:
        dst.write(read_dataset_year, window=Window(col_off, row_off, width, height), indexes=1)
    raster_dataset_year.close()

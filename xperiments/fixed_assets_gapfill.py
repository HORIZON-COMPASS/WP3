import pandas as pd
import numpy as np
from exposure_functions import copula_inference_Frank, copula_fit_frank, prepare_fixed_asset_data

## Define input data
exposure_file = 'C:/HANZE2_products/Compass_exposure/National_exposure_all.xlsx'
Fixed_asset_raw = pd.read_excel(open(exposure_file, 'rb'), sheet_name='Fixed_assets_to_GDP_raw', index_col='ISOn')
GDPpc = pd.read_excel(open(exposure_file, 'rb'), sheet_name='GDP_per_capita_2017$', index_col='ISOn')
Countries = range(0,248)
Years = range(1850,2024)

### Prepare fixed asset data
Combined_data_dz = prepare_fixed_asset_data(Fixed_asset_raw, GDPpc)

np.savetxt('C:/HANZE2_products/Compass_exposure/Fixed_asset_GDPpc.csv', Combined_data_dz, delimiter=",", fmt="%f")

### Fit Frank copula to the data
copula_assets, copula_samples = copula_fit_frank(Combined_data_dz)

### Estimate fixed asset per country and year
GDPpc_all = GDPpc.values[:,3:].astype(float)
Fixed_asset_raw_all = Fixed_asset_raw.values[:,3:].astype(float)
Fixed_asset_pred = np.zeros([len(Countries),len(Years)])
for c in Countries:
    print(str(c))
    Fixed_asset_pred_c = np.zeros([1,len(Years)])
    for y in Years:
        GDPpc_cy = GDPpc_all[c,y-1850]
        Fixed_asset_pred_c[0,y-1850] = np.mean(copula_inference_Frank(copula_assets, copula_samples, GDPpc_cy))
    asset_avail = ~np.isnan(Fixed_asset_raw_all[c, :])
    if sum(asset_avail)==0:
        Fixed_asset_pred[c,:] = Fixed_asset_pred_c
    else:
        Fixed_asset_pred[c, asset_avail] = Fixed_asset_raw_all[c, asset_avail]
        Index_first = np.where(asset_avail == 1)[0][0]
        Index_last = np.where(asset_avail == 1)[0][-1]
        Fixed_asset_first = Fixed_asset_raw_all[c, Index_first]
        Fixed_asset_last = Fixed_asset_raw_all[c, Index_last]
        Fixed_asset_pred[c, 0:Index_first] = Fixed_asset_pred_c[0,0:Index_first] * Fixed_asset_first / Fixed_asset_pred_c[0,Index_first]
        Fixed_asset_pred[c, Index_last:] = Fixed_asset_pred_c[0,Index_last:] * Fixed_asset_last / Fixed_asset_pred_c[0,Index_last]

Fixed_asset_pred_df = pd.DataFrame(data=Fixed_asset_pred, columns=Fixed_asset_raw.columns[3:],index=Fixed_asset_raw.index)
Fixed_asset_filled = pd.concat([Fixed_asset_raw[['ISO2','ISO3','Name']],Fixed_asset_pred_df], axis=1)
Fixed_asset_filled.to_csv('C:/HANZE2_products/Compass_exposure/Fixed_asset_prediction_historical.csv', sep=',')
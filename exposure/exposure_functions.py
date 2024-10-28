import pandas as pd
import numpy as np
from copulas.bivariate import Frank
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
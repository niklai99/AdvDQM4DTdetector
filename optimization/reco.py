import pandas as pd
from pandas.core.indexes.numeric import IntegerIndex
import numpy as np
from scipy import optimize
from numpy import sqrt


# *****************************************************************************
# LINEAR_REG
# *****************************************************************************


def chisq(X, Y, SY, a, b):
    return sum(((y - a - x * b) / sy) ** 2 for x, y, sy in zip(X, Y, SY))


def fitfunc(x, a, b):
    return a + b * x


def linear_reg(X, Y):

    sigma_X = [0.4] * len(X)  # 400 um std
    mGuess = 100 if ((X[0] - X[1]) == 0) else (Y[0] - Y[1]) / (X[0] - X[1])
    qGuess = Y[0] - mGuess * X[0]
    p_init = [qGuess, mGuess]  # valori iniziali
    p_best, pcov = optimize.curve_fit(fitfunc, Y, X, sigma=sigma_X, p0=p_init)

    chi2 = chisq(Y, X, sigma_X, p_best[0], p_best[1])
    dof = len(X) - 2  # - 1
    chisq_comp = abs(chi2 - dof) / sqrt(2 * dof)

    m = p_best[1]
    q = p_best[0]
    return {"m": m, "q": q, "chisq_comp": chisq_comp}


# *****************************************************************************
# COMBINATE LOCAL
# *****************************************************************************

from itertools import combinations


def compute(df): 
    
    comb = []
    if len(df.LAYER.unique()) == 3:
        comb.append(df)
        tot_Hits = 3
    else:
        for index in list(combinations(df.index, 4)):
            if len(df.loc[index, :].LAYER.unique()) == 4:
                comb.append(df.loc[index, :]) 
        tot_Hits = 4

    min_lambda = np.finfo(float).max

    for data in comb:
        X = np.array(pd.concat([data["X_RIGHT_GLOB"], data["X_LEFT_GLOB"]]))
        Y = np.array(pd.concat([data["WIRE_Z_GLOB"], data["WIRE_Z_GLOB"]]))
        for indexes_comb in list(combinations(range(len(X)), tot_Hits)):
            indexes_comb = list(indexes_comb)
            if len(np.unique(Y[indexes_comb])) == tot_Hits:
                regr_dict = linear_reg(X[indexes_comb], Y[indexes_comb])
                if abs(regr_dict["chisq_comp"]) < min_lambda:
                    min_lambda = abs(regr_dict["chisq_comp"])
                    xdata = X[indexes_comb]
                    res_dict = regr_dict
                    best_comb = indexes_comb
                    best_data = data

    reco_df = pd.concat([best_data, best_data], axis=0, ignore_index=True)
    reco_df = reco_df.loc[best_comb, :]
    reco_df["m"] = np.full(len(reco_df), res_dict["m"])
    reco_df["q"] = np.full(len(reco_df), res_dict["q"])
    reco_df["X"] = xdata
    if xdata is None: return

    return reco_df
""""
def computeOpt(df):  

    if len(df.LAYER.unique()) == 3:
        tot_Hits = 3
    else:
        tot_Hits = 4

    flag = True

    X = np.array(pd.concat([df["X_RIGHT_GLOB"], df["X_LEFT_GLOB"]]))
    Y = np.array(pd.concat([df["WIRE_Z_GLOB"], df["WIRE_Z_GLOB"]]))
    for indexes_comb in list(combinations(range(len(X)), tot_Hits)):
        indexes_comb = list(indexes_comb)
        if len(np.unique(Y[indexes_comb])) == tot_Hits:
            regr_dict = linear_reg(X[indexes_comb], Y[indexes_comb])
            if flag:
                min_lambda = abs(regr_dict["chisq_comp"])
                xdata = X[indexes_comb]
                res_dict = regr_dict
                flag = False
                best_comb = indexes_comb
            elif abs(regr_dict["chisq_comp"]) < min_lambda:
                min_lambda = abs(regr_dict["chisq_comp"])
                xdata = X[indexes_comb]
                res_dict = regr_dict
                best_comb = indexes_comb

    reco_df = pd.concat([df, df], axis=0, ignore_index=True)
    reco_df = reco_df.loc[best_comb, :]
    reco_df["m"] = np.full(len(reco_df), res_dict["m"])
    reco_df["q"] = np.full(len(reco_df), res_dict["q"])
    reco_df["X"] = xdata
    if xdata is None: return

    return reco_df

"""
# *****************************************************************************
# COMPUTE EVENT
# *****************************************************************************

def computeEvent(df_E):

    chamber = [df_E[df_E["SL"] == i] for i in range(4)]
    event_reco_df = pd.DataFrame()

    for df in chamber:
        if len(pd.unique(df.LAYER)) < 3:
            continue
        
        chamber_reco_df = compute(df)
        event_reco_df = pd.concat(
            [event_reco_df, chamber_reco_df], axis=0, ignore_index=True
        )

    if len(event_reco_df)==0:
        return None

    return event_reco_df


# *****************************************************************************
# GET RESULTS
# *****************************************************************************


def getRecoResults(events):
    resultsDf = []

    for df_E in events:
        event_reco_df = computeEvent(df_E)
        if event_reco_df is None:
            continue
        if len(event_reco_df)==0:
            continue
        resultsDf.append(event_reco_df)

    return resultsDf

# *****************************************************************************
# MULTIPROCESSING
# *****************************************************************************
from multiprocessing import Pool, cpu_count

def getRecoResults_mp(events):
    
    pool = Pool(processes=cpu_count()-2)
  
    result = pool.map_async(computeEvent, events)
    resultsDf = result.get()
    pool.close()
    pool.join()
    resultsDf = [x for x in resultsDf if x is not None]

    return resultsDf

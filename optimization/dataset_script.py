import pandas as pd
import numpy as np
import yaml
import math
import warnings
import argparse

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.filterwarnings("ignore")


from eventsFactory import getEvents
from reco import getRecoResults, getRecoResults_mp

"""USAGE:

    python dataset_script.py -i <input_data_directory> -o <output_data_directory> -c <config_directory> -run <last_4_digits_of_run>
    
    The I/O directories should be ../data/ (as default)
    
    The configuration directories should be ../config/ (as default)
    
    NOTE that data and config files should be named accordingly
    
    EXAMPLE: 
    
    python dataset_script.py -run 0054 
    
"""

# CONSTANTS
#USE_TRIGGER = False
RUN_TIME_SHIFT = 0
KEEP = ["FPGA", "TDC_CHANNEL", "HIT_DRIFT_TIME", "D_WIRE_HIT", "m"]



def argParser():
    """manages command line arguments"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", type=str, default="../data/", help="input data directory"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="../data/", help="output data directory"
    )
    parser.add_argument(
        "-c", "--config", type=str, default="../config/", help="config directory"
    )
    parser.add_argument("-run", "--run", type=str, default="0054", help="run number")
    parser.add_argument("-mp", "--multiprocessing", dest="multiprocessing", action='store_true', help="multiprocessing")
    parser.add_argument("-no-mp", "--no--multiprocessing", dest="multiprocessing", action='store_false', help="no multiprocessing")
    parser.set_defaults(multiprocessing=True)
    return parser.parse_args()


def buildDataframe(df_fname, cfg, MULTIPROCESSING):

    df = pd.DataFrame()

    print("Getting events...")
    events = getEvents(df_fname, cfg, RUN_TIME_SHIFT)
    print("Reconstructing tracks...")
    if MULTIPROCESSING:
        print("Using multiprocessing...")
        resultsDf = getRecoResults_mp( events )
    else:
        print("Without multiprocessing...")
        resultsDf = getRecoResults( events )
    print("Building dataframe...")
    # out df
    for df_ in resultsDf:
        df_["D_WIRE_HIT"]= df_["X"]-df_["WIRE_X_GLOB"]
        df_ = df_[KEEP]
    df = pd.concat(resultsDf, axis=0, ignore_index=True)
    
    # add a sequential channel tag
    df.loc[(df["FPGA"] == 0), "CH"] = df["TDC_CHANNEL"]
    df.loc[(df["FPGA"] == 1), "CH"] = df["TDC_CHANNEL"] + 128
    df_ = df.drop(["FPGA", "TDC_CHANNEL"], axis=1) 
    df_["CH"] = df_["CH"].astype(np.uint8)

    # clean dataset
    df = df_[["CH", "HIT_DRIFT_TIME",'D_WIRE_HIT', "m"]]
    df = df[(df["HIT_DRIFT_TIME"] > -200) & (df["HIT_DRIFT_TIME"] < 600)]
    df = df[(df['D_WIRE_HIT'] > -21) & (df['D_WIRE_HIT'] < 21)]

    # rad to deg conversion
    df["THETA"] = np.arctan(df["m"]) * 180.0 / math.pi

    # create sl column
    df["SL"] = df["CH"]//64
    df["SL"][df["SL"]<2] = [int(not x) for x in df["SL"]]

    print("Dataframe ready!")

    return df


def saveChannels(df, OUTPUT_PATH, RUNNUMBER):

    FILE_NAME = f"RUN00{RUNNUMBER}_channels.h5"
    save_to = OUTPUT_PATH + FILE_NAME

    print("Saving data...")

    for sl in np.unique(df["SL"]):
        for channel in np.unique(df[df["SL"] == sl]["CH"]): 
            df[(df["SL"] == sl) & (df["CH"] == channel)].to_hdf(save_to, key=f"sl{sl}/ch{channel}", mode="a")

    return


def main(args):

    # store command line arguments
    DATA_PATH = args.input
    CONFIG_PATH = args.config
    RUNNUMBER = args.run
    OUTPUT_PATH = args.output
    MULTIPROCESSING = args.multiprocessing


    # link data and config files
    data_file = DATA_PATH + f"RUN00{RUNNUMBER}_data.txt"
    config_file = CONFIG_PATH + f"RUN00{RUNNUMBER}.yml"

    # read config from file
    print("Reading config from file...")
    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

    df = buildDataframe(data_file, cfg, MULTIPROCESSING)
    saveChannels(df, OUTPUT_PATH, RUNNUMBER)

    return


if __name__ == "__main__":
    args = argParser()
    main(args)

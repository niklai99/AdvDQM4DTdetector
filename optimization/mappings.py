from constants import XCELL, X_POS_SHIFT, Z_POS_SHIFT

class Mapping(object):
    def __init__(self, cfg):
        self.cfg = cfg

    def sl_map(self, df):
        """
        Add columns with SL, LAYER, WIRE_NUM, WIRE_POS
        for local coordinates
        Args:
            - df  : Pandas dataframe of hits
            - cfg : configuration dict for this run
        """
        print("local mapping...")
        # assing SL to each hit
        # sl_cfg is similar to {"fpga": 0, "ch_start": 0, "ch_end": 63}
        for sl, sl_cfg in self.cfg["sl_mapping"].items():
            sl_mask = (
                (df["FPGA"] == sl_cfg["fpga"])
                & (df["TDC_CHANNEL"] >= sl_cfg["ch_start"])
                & (df["TDC_CHANNEL"] <= sl_cfg["ch_end"])
            )
            df.loc[sl_mask, "SL"] = sl
        
        # create the layer column (layer 4 is the top one)
        df.loc[(df["TDC_CHANNEL"] % 4 == 0), "LAYER"] = 4
        df.loc[(df["TDC_CHANNEL"] % 4 == 2), "LAYER"] = 3
        df.loc[(df["TDC_CHANNEL"] % 4 == 1), "LAYER"] = 2
        df.loc[(df["TDC_CHANNEL"] % 4 == 3), "LAYER"] = 1

        df = df.astype({"SL": "uint8", "LAYER": "uint8"})
        # set the wire num inside the layer: ranging from 1 to 16 (left to right)
        # tdc_channel is normalized from 0->63 for each sl
        # assign the wire position
        for layer in [1, 2, 3, 4]:
            # local wire x position
            df.loc[df["LAYER"] == layer, "WIRE_X_LOC"] = (
                df["TDC_CHANNEL"] % 64 // 4
            ) * XCELL + X_POS_SHIFT[layer]

            # local wire z position
            df.loc[df["LAYER"] == layer, "WIRE_Z_LOC"] = Z_POS_SHIFT[layer]

        return df

    def global_map(self, df):
        """
        Create global coordinates based on the SL geometry
        adopted in the selected run
        Args:
            - df  : Pandas dataframe of hits
            - cfg : configuration dict for this run
        """
        # build the map for each sl
        df = self.sl_map(df)
        print("global mapping...")
        # place wire in the space
        for sl, sl_shift in self.cfg["sl_shift"].items():
            # shift z
            df.loc[df["SL"] == sl, "WIRE_Z_GLOB"] = df["WIRE_Z_LOC"] + sl_shift["z"]

            # shift x
            df.loc[df["SL"] == sl, "WIRE_X_GLOB"] = df["WIRE_X_LOC"] + sl_shift["x"]

            # shift y -> not implemented

        return df

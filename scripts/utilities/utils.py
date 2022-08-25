import pandas as pd
import janitor
import os
import gc


def get_fulldata(directory="../data/bihar_land_records_csv/", **pandas_kwargs):
    final_df = []
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        lr_file = pd.read_csv(f, low_memory=False, **pandas_kwargs)
        final_df.append(lr_file)

    final_frame = pd.concat(final_df, axis=0, ignore_index=True)
    del final_df
    gc.collect()

    return final_frame

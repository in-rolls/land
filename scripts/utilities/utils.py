import pandas as pd
import janitor
import os
import gc


def get_fulldata(directory="../data/bihar_land_records_csv/", **pandas_kwargs):
    final_df = []
    for filename in os.listdir(directory):
        if not filename.endswith('.csv'):
            continue
        f = os.path.join(directory, filename)
        lr_file = pd.read_csv(f, **pandas_kwargs)
        final_df.append(lr_file)

    final_frame = pd.concat(final_df, axis=0, ignore_index=True)
    del final_df
    gc.collect()

    return final_frame

def pandas_to_tex(df, texfile, index=False, **kwargs):
    if texfile.split(".")[-1] != ".tex":
        texfile += ".tex"

    tex_table = df.to_latex(index=index, header=False, **kwargs)
    tex_table_fragment = "\n".join(tex_table.split("\n")[3:-3])
    # Remove the last \\ in the tex fragment to prevent the annoying
    # "Misplaced \noalign" LaTeX error when I use \bottomrule
    # tex_table_fragment = tex_table_fragment[:-2]

    with open(texfile, "w") as tf:
        tf.write(tex_table_fragment)
    return None
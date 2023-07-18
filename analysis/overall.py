import pandas as pd
import numpy as np
import os
import seaborn as sns
import tol_colors as tc
import argparse
from datetime import datetime
from datetime import timezone
from matplotlib import pyplot as plt

def info(verbose, msg):
    if verbose:
        print(f"[INFO] {msg}")

def plot_license_type(contents, ax):
    permissive_licenses = ["mit", "gpl-3.0", "apache-2.0", "bsd-3-clause", "gpl-2.0", "bsd-2-clause"] # https://en.wikipedia.org/wiki/Permissive_software_license
    contents.license = contents.license.fillna('None')
    contents["license_type"] = np.where(
        contents.license.isin(permissive_licenses), "permissive", np.where(
        contents.license == "None", "None", np.where(
        contents.license == "other", "unknown", "non-permissive")))
    contents.license_type.value_counts().plot(
        kind='bar',
        ax=ax,
        xlabel="license type",
        ylabel="count"
    )

def main(data_dir, verbose):
    info(verbose, "Loading data...")
    contents = pd.read_csv(os.path.join(data_dir, "contents.csv"), index_col=0)
    
    info(verbose, "Plotting...")
    fig, axs = plt.subplots(ncols=2, figsize=(8, 4))
    plot_license_type(contents, axs[0])
    plt.savefig(os.path.join(data_dir, "overall.png"), bbox_inches="tight")

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="overall",
        description="Plot overall repo analysis."
    )
    parser.add_argument("--dir", default="../data/analysis", type=str, help="path to data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.dir, args.verbose)
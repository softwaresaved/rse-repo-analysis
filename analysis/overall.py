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
    contents.license_type.value_counts().sort_index().plot(
        kind='bar',
        ax=ax,
        xlabel="license type",
        ylabel="repository count"
    )
    ax.bar_label(ax.containers[0])
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

def plot_contributing_file_present(contents, ax):
    pd.notna(contents.contributing_added).value_counts().plot(
        kind='bar',
        ax=ax,
        xlabel="contributing file",
        ylabel="repository count"
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

def plot_emojis(contents, ax):
    counts, bins = np.histogram(contents.readme_emojis, [0, 1, 2, 5, 10, contents.readme_emojis.max()])
    binlabels = [f"[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"[{bins[-2]} - {bins[-1]}]"]
    ax.bar(binlabels, counts)
    ax.bar_label(ax.containers[0])
    ax.set(xlabel="number of emojis in README", ylabel="repository count")

def plot_team_size(metadata, contributions, ax):
    contrib_df = pd.merge(metadata[["github_user_cleaned_url", "created_at"]], contributions)
    contrib_df["week_since_repo_creation"] = (contrib_df.week_co - contrib_df.created_at).dt.days // 7
    team_df = contrib_df[["github_user_cleaned_url", "author", "week_since_repo_creation", "commits"]].set_index(["github_user_cleaned_url", "author", "week_since_repo_creation"]).sort_index()
    # user is active contributor if made at least one commit in last 12 weeks
    windowed_team_df = team_df.groupby(level="author").rolling(window=12, min_periods=0).sum().droplevel(0)
    windowed_team_df["active contributors"] = windowed_team_df.commits > 0
    # team size
    team_size = windowed_team_df.groupby(level=["github_user_cleaned_url", "week_since_repo_creation"])["active contributors"].value_counts()[:,:,True]
    max_team_size = team_size.groupby(level="github_user_cleaned_url").max()
    counts, bins = np.histogram(max_team_size, [0, 1, 2, 3, 5, 10, max_team_size.max()])
    binlabels = [f"[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"[{bins[-2]} - {bins[-1]}]"]
    ax.bar(binlabels, counts)
    ax.bar_label(ax.containers[0])
    ax.set(xlabel="maximum team size", ylabel="repository count")

def main(data_dir, verbose):
    info(verbose, "Loading data...")
    contents = pd.read_csv(os.path.join(data_dir, "contents.csv"), index_col=0)
    metadata = pd.read_csv(os.path.join(data_dir, "metadata.csv"), index_col=0)
    metadata["created_at"] = pd.to_datetime(metadata.created_at)
    contributions = pd.read_csv(os.path.join(data_dir, "contributions.csv"), index_col=0)
    contributions["week_co"] = pd.to_datetime(contributions.week_co)

    info(verbose, "Plotting...")
    fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(12, 12))
    fig.tight_layout(h_pad=8, w_pad=5, rect=(0.05, 0.05, 0.95, 0.95))
    plot_license_type(contents, axs[0][0])
    plot_emojis(contents, axs[0][1])
    plot_contributing_file_present(contents, axs[1][0])
    plot_team_size(metadata, contributions, axs[1][1])
    plt.suptitle("Overall statistics for ePrints repositories")
    plt.savefig(os.path.join(data_dir, "overall.png"))#, bbox_inches="tight")

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="overall",
        description="Plot overall repo analysis."
    )
    parser.add_argument("--dir", default="../data/analysis", type=str, help="path to data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.dir, args.verbose)
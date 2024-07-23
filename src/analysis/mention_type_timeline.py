import argparse
import os
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta

SMALL_SIZE = 24
MEDIUM_SIZE = 30

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
#plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=SMALL_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=MEDIUM_SIZE)  # fontsize of the figure title

def main(githubdir, outdir):
    # load data mapping ePrints publication data to intent (produced by repo_intent.py)
    eprints_df = pd.read_csv(os.path.join(outdir, "eprints_w_intent.csv"), index_col=0)
    # load GitHub metadata
    metadata_df = pd.read_csv(os.path.join(githubdir, "metadata.csv"), index_col=0)
    # combine data
    df = eprints_df.merge(metadata_df[["github_user_cleaned_url", "created_at"]], left_on="github_repo_id", right_on="github_user_cleaned_url")
    df["eprints_date"] = pd.to_datetime(df.eprints_date)
    df["created_at"] = pd.to_datetime(df.created_at)
    df["mention type"] = np.where(df["mention_created"], "created", "not created")
    # plot repo creation date against date listed in ePrints entry (assumed to be publication date)
    fig, ax = plt.subplots(figsize=(10,8))
    ax.grid(True)
    
    xlim = [df["created_at"].min(), df["created_at"].max()]
    year_one = [d + timedelta(days=365) for d in xlim]
    year_two = [d + timedelta(days=2*365) for d in xlim]
    year_three = [d + timedelta(days=3*365) for d in xlim]
    ax.plot(xlim, xlim, color="black", linewidth=0.75)
    ax.fill_between(xlim, xlim, year_one, color="grey", alpha=0.3)
    ax.fill_between(xlim, xlim, year_two, color="grey", alpha=0.2)
    ax.fill_between(xlim, xlim, year_three, color="grey", alpha=0.1)
    ax = sns.scatterplot(
        ax = ax,
        data = df,
        x = "created_at",
        y = "eprints_date",
        hue="mention type",
        s=80
    )

    h,l = ax.get_legend_handles_labels()
    ax.legend_.remove()
    ax.legend(h, l, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.13), borderpad=0.2)

    ax.set(xlabel="GitHub repository creation date",
           ylabel="publication date")  # it's usually the publication date, though not always
    ax.set_title("Mention type depending on difference\nbetween repo creation and publication date", pad=45)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "plots/overall/mention_type_timeline.png"), bbox_inches="tight", transparent=True)

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="mention_type_timeline",
        description="Plot mention type (created/not created) against the repo creation date and publication date."
    )
    parser.add_argument("--githubdir", default="../../data/raw/github", type=str, help="path to GitHub data directory")
    parser.add_argument("--outdir", default="../../data/derived", type=str, help="path to use for output data")
    args = parser.parse_args()
    main(args.githubdir, args.outdir)
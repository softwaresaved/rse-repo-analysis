import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta

def main():
    eprints_df = pd.read_csv("../data/outputs/eprints_w_intent.csv", index_col=0)
    metadata_df = pd.read_csv("../data/analysis/metadata.csv", index_col=0)
    df = eprints_df.merge(metadata_df[["github_user_cleaned_url", "created_at"]], left_on="github_repo_id", right_on="github_user_cleaned_url")
    df["eprints_date"] = pd.to_datetime(df.eprints_date)
    df["created_at"] = pd.to_datetime(df.created_at)
    df["mention type"] = np.where(df["mention_created"], "created", "not created")
    ax = plt.axes()
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
    )
    ax.set(xlabel="GitHub repository creation date",
           ylabel="publication date")  # it's usually the publication date, though not always
    ax.set_title("Mention type depending on distance between repo creation and publication date")
    plt.tight_layout()
    plt.savefig("../data/analysis/overall/mention_type_timeline.png")

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="mention_type_timeline",
        description="Plot mention type (created/not created) against the repo creation date and publication date."
    )
    main()
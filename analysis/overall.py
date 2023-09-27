import pandas as pd
import numpy as np
import os
import argparse
import ast
import string
import re
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from matplotlib import pyplot as plt

def info(verbose, msg):
    if verbose:
        print(f"[INFO] {msg}")

def clean_heading(h):
    to_remove = string.digits + string.whitespace + ".:"
    h = h.lstrip(to_remove)
    pattern = "\[(.+?)\]\(.+?\)"
    h = re.sub(pattern, r'\1', h, count=0)
    h = h.replace(string.punctuation, "")
    h = h.strip(string.punctuation)
    h = h.lower()
    return h

def plot_license_type(contents, ax):
    contents = contents.copy()
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
    ax.bar_label(ax.containers[0])
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

def plot_emojis(contents, ax):
    bins = [0, 1, 2, 5, 10]
    if contents.readme_emojis.max() > bins[-1]:
        bins.append(contents.readme_emojis.max())
    counts, bins = np.histogram(contents.readme_emojis, bins)
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
    bins = [1, 2, 5, 10]
    if max_team_size.max() > bins[-1]:
        bins.append(max_team_size.max())
    counts, bins = np.histogram(max_team_size, bins)
    binlabels = [f"[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"[{bins[-2]} - {bins[-1]}]"]
    ax.bar(binlabels, counts)
    ax.bar_label(ax.containers[0])
    ax.set(xlabel="maximum team size", ylabel="repository count")

def plot_readme_size(contents, ax, type="bar"):
    bins = [0, 1, 300, 1500, 10000]
    binmeanings = ["none", "ultra-short", "short", "informative", "detailed"]
    if contents.readme_size.max() > bins[-1]:
        bins.append(contents.readme_size.max())
    counts, bins = np.histogram(contents.readme_size, bins)
    binlabels = [f"{binmeanings[i]}\n[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"{binmeanings[-1]}\n[{bins[-2]} - {bins[-1]}]"]
    if type=="bar":
        ax.bar(binlabels, counts)
        ax.bar_label(ax.containers[0])
        ax.tick_params(axis='x', labelrotation=45)
        ax.set(xlabel="size of README in Bytes", ylabel="repository count")
    elif type=="pie":
        ax.pie(counts, labels=binlabels, autopct='%1.1f%%')
        ax.set(xlabel="size of README in Bytes")

def plot_headings(readme_df, ax):
    headings = []
    for l in readme_df.added_headings.dropna():
        headings += ast.literal_eval(l)
    headings = [clean_heading(h) for h in headings]

    stopwords = STOPWORDS
    custom = set(["trades", "glosat", "glosat_table_dataset", "nilmtk", "bert", "lemon", "cascadetabnet"])
    stopwords = stopwords.union(custom)
    wordcloud = WordCloud(
        collocation_threshold=15,
        stopwords=stopwords,
        scale=10,
        background_color="white",
        random_state=42
        ).generate(" ".join(headings))
    ax.imshow(wordcloud)
    ax.set_axis_off()
    ax.set(title="README headings")

def main(data_dir, verbose, filter_path, tag):
    info(verbose, "Loading data...")
    contents = pd.read_csv(os.path.join(data_dir, "contents.csv"), index_col=0)
    metadata = pd.read_csv(os.path.join(data_dir, "metadata.csv"), index_col=0)
    metadata["created_at"] = pd.to_datetime(metadata.created_at)
    contributions = pd.read_csv(os.path.join(data_dir, "contributions.csv"), index_col=0)
    contributions["week_co"] = pd.to_datetime(contributions.week_co)
    readme_df = pd.read_csv(os.path.join(data_dir, "readme_history.csv"), index_col=0)

    if filter_path is not None:
        info(verbose, "Filtering data...")
        with open(filter_path, "r") as f:
            filtered = [line.rstrip() for line in f]
        contents = contents.loc[contents.github_user_cleaned_url.isin(filtered)]
        metadata = metadata.loc[metadata.github_user_cleaned_url.isin(filtered)]
        contributions = contributions.loc[contributions.github_user_cleaned_url.isin(filtered)]
        readme_df = readme_df.loc[readme_df.github_user_cleaned_url.isin(filtered)]

    info(verbose, "Plotting...")
    fig, axs = plt.subplots(ncols=3, nrows=2, figsize=(18, 12))
    fig.tight_layout(h_pad=8, w_pad=5, rect=(0.05, 0.05, 0.95, 0.95))
    plot_license_type(contents, axs[0][0])
    plot_emojis(contents, axs[0][1])
    plot_contributing_file_present(contents, axs[1][0])
    plot_team_size(metadata, contributions, axs[1][1])
    plot_readme_size(contents, axs[0][2], type="pie")
    plot_headings(readme_df, axs[1][2])
    if tag:
        plt.suptitle(f"Overall statistics for ePrints repositories ({tag})")
        plt.savefig(os.path.join(data_dir, "overall", f"overall_{tag}.png"))#, bbox_inches="tight")
    else:
        plt.suptitle("Overall statistics for ePrints repositories")
        plt.savefig(os.path.join(data_dir, "overall", "overall.png"))#, bbox_inches="tight")

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="overall",
        description="Plot overall repo analysis."
    )
    parser.add_argument("--dir", default="../data/analysis", type=str, help="path to data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    parser.add_argument("--filter", type=str, help="path to file with repos to consider")
    parser.add_argument("--tag", type=str, help="tag name to use")
    args = parser.parse_args()
    main(args.dir, args.verbose, args.filter, args.tag)
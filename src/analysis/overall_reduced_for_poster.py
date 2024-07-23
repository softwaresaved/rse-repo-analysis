import pandas as pd
import numpy as np
import os
import argparse
import ast
import string
import re
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from datetime import datetime

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

def info(verbose, msg):
    if verbose:
        print(f"[INFO] {msg}")

def clean_heading(h):
    """Clean and normalise extracted headings.

    Args:
        h (str): heading text

    Returns:
        str: cleaned heading
    """
    # remove leading non-word characters
    to_remove = string.digits + string.whitespace + ".:"
    h = h.lstrip(to_remove)
    # remove markdown-style links
    pattern = r"\[(.+?)\]\(.+?\)"
    h = re.sub(pattern, r'\1', h, count=0)
    # remove any punctuation and convert to lower-case
    h = h.replace(string.punctuation, "")
    h = h.strip(string.punctuation)
    h = h.lower()
    return h

def plot_license_type(contents, ax):
    """Plot a bar chart indicating the number of repositories with permissive, non-permissive, unknown type license or no license at all.

    Args:
        contents (pd.DataFrame): contents data mined from GitHub
        ax (Axes): subplot to use
    """
    contents = contents.copy()
    permissive_licenses = ["mit", "gpl-3.0", "apache-2.0", "bsd-3-clause", "gpl-2.0", "bsd-2-clause"] # https://en.wikipedia.org/wiki/Permissive_software_license
    contents.license = contents.license.fillna('None')
    # If not permissive, check if it's non-existent or type other, otherwise class as non-permissive
    contents["license_type"] = np.where(
        contents.license.isin(permissive_licenses), "permissive", np.where(
        contents.license == "None", "None", np.where(
        contents.license == "other", "unknown", "non-permissive")))
    # plot value counts
    contents.license_type.value_counts().sort_index().plot(
        kind='barh',
        ax=ax,
        #ylabel="license type",
        #xlabel="repository count"
    )
    ax.bar_label(ax.containers[0])
    ax.set_title("license type")
    #ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

def plot_contributing_file_present(contents, ax):
    """Plot a bar chart visualising the number of repositories with contribution guidelines.

    Args:
        contents (pd.DataFrame): contents data mined from GitHub
        ax (Axes): subplot to use
    """
    pd.notna(contents.contributing_added).value_counts().plot(
        kind='barh',
        ax=ax,
        #ylabel="contributing file",
        #xlabel="repository count"
    )
    ax.bar_label(ax.containers[0])
    ax.set_title("contributing file present")
    #ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

def plot_team_size(metadata, contributions, ax):
    """Plot a histogram visualising the maximum team size for a repository.

    Args:
        metadata (pd.DataFrame): metadata mined from GitHub
        contributions (pd.DataFrame): contributions (i.e. commit) data mined from GitHub
        ax (Axes): subplot to use
    """
    contrib_df = pd.merge(metadata[["github_user_cleaned_url", "created_at"]], contributions)
    # add week timeline info
    contrib_df["week_since_repo_creation"] = (contrib_df.week_co - contrib_df.created_at).dt.days // 7
    team_df = contrib_df[["github_user_cleaned_url", "author", "week_since_repo_creation", "commits"]].set_index(["github_user_cleaned_url", "author", "week_since_repo_creation"]).sort_index()
    # user is considered an active contributor if they made at least one commit in the last 12 weeks
    windowed_team_df = team_df.groupby(level="author").rolling(window=12, min_periods=0).sum().droplevel(0)
    windowed_team_df["active contributors"] = windowed_team_df.commits > 0
    # team size: number of active contributors within one week
    team_size = windowed_team_df.groupby(level=["github_user_cleaned_url", "week_since_repo_creation"])["active contributors"].value_counts()[:,:,True]
    max_team_size = team_size.groupby(level="github_user_cleaned_url").max()
    # plot histogram
    bins = [1, 2, 5, 10]
    if max_team_size.max() > bins[-1]:
        bins.append(max_team_size.max())
    counts, bins = np.histogram(max_team_size, bins)
    binlabels = [f"[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"[{bins[-2]} - {bins[-1]}]"]
    ax.barh(binlabels, counts)
    ax.bar_label(ax.containers[0])
    #ax.set(ylabel="maximum team size", xlabel="repository count")
    ax.set(xlabel="repository count")
    ax.set_title("maximum team size")

def plot_readme_size(contents, ax, type="bar"):
    """Plot a histogram of the size of the README file found in repositories. The bin limits were chosen empirically.

    Args:
        contents (pd.DataFrame): contents data mined from GitHub
        ax (Axes): subplot to use
        type (str, optional): plot type, can be "bar" or "pie". Defaults to "bar".
    """
    bins = [0, 1, 300, 1500, 10000]
    binmeanings = ["none", "ultra-short", "short", "informative", "detailed"]
    colours = ["#3875b1", "#f1882e", "#4d9d39", "#c73f30", "#8e6aba"]
    if contents.readme_size.max() > bins[-1]:
        bins.append(contents.readme_size.max())
    counts, bins = np.histogram(contents.readme_size, bins)
    binlabels = [f"{binmeanings[i]}\n[{bins[i]} - {bins[i+1]})" for i in range(len(bins)-2)]
    binlabels += [f"{binmeanings[-1]}\n[{bins[-2]} - {bins[-1]}]"]
    if type=="bar":
        ax.barh(binlabels, counts)
        ax.bar_label(ax.containers[0])
        ax.tick_params(axis='x', labelrotation=45)
        ax.set(ylabel="size of README in Bytes", xlabel="repository count")
    elif type=="pie":
        # remove empty bins
        ax.pie(counts[np.nonzero(counts)], labels=np.array(binlabels)[np.nonzero(counts)], autopct='%1.1f%%', colors=np.array(colours)[np.nonzero(counts)])
        ax.set(xlabel="size of README in Bytes")

def plot_headings(readme_df, ax):
    """Plot a wordcloud from the headings used in README files. Excludes some manually defined words that skew the results too much to be meaningful.

    Args:
        readme_df (pd.DataFrame): readme history data mined from GitHub, including all headings ever added to the README
        ax (Axes): subplot to use
    """
    # clean any existing headings
    headings = []
    for l in readme_df.added_headings.dropna():
        headings += ast.literal_eval(l)
    headings = [clean_heading(h) for h in headings]

    # manually exclude words that were found to skew the distribution
    stopwords = STOPWORDS
    custom = set(["trades", "glosat", "glosat_table_dataset", "nilmtk", "bert", "lemon", "cascadetabnet"])
    stopwords = stopwords.union(custom)
    # plot wordcloud
    wordcloud = WordCloud(
        collocation_threshold=15,
        stopwords=stopwords,
        scale=10,
        background_color="white",
        random_state=42
        ).generate(" ".join(headings))
    ax.set_axis_off()
    ax.imshow(wordcloud)
    ax.set(title="README headings")

def plot_table(metadata, stars, forks, ax):
    """Add a table with basic stats (repository age, fork counts, star counts).

    Args:
        metadata (pd.DataFrame): metadata mined from GitHub.
        stars (pd.DataFrame): stars data mined from GitHub.
        forks (pd.DataFrame): forks data mined from GitHub.
        ax (Axes): subplot to use
    """
    age = (datetime.today() - metadata["created_at"]).dt.days // 7
    fork_counts = forks.groupby("github_user_cleaned_url")["user"].count()
    fork_counts.rename("forks_no", inplace=True)
    star_counts = stars.groupby("github_user_cleaned_url")["user"].count()
    star_counts.rename("stars_no", inplace=True)
    cell_text = [
        [f"{age.mean():.2f}", f"{fork_counts.mean():.2f}", f"{star_counts.mean():.2f}"],
        [f"{age.std():.2f}", f"{fork_counts.std():.2f}", f"{star_counts.std():.2f}"],
        [f"{age.median():.0f}", f"{fork_counts.median():.0f}", f"{star_counts.median():.0f}"],
        [f"{age.min():.0f}", f"{fork_counts.min():.0f}", f"{star_counts.min():.0f}"],
        [f"{age.max():.0f}", f"{fork_counts.max():.0f}", f"{star_counts.max():.0f}"],
    ]
    table = ax.table(cellText=cell_text,
                     colLabels=["age (weeks)", "forks", "stars"],
                     rowLabels=["mean", "std", "median", "min", "max"],
                     colWidths=[0.4, 0.3, 0.3],
                     loc='center right',
                     #bbox=(0, 0, 1, 1)
                     )
    table.auto_set_font_size(False)
    table.set_fontsize(SMALL_SIZE)
    table.scale(1, 3)
    ax.set_axis_off()
    ax.set_title("Summary statistics", pad=25)

def main(data_dir, outdir, verbose, filter_path, tag):
    info(verbose, "Loading data...")
    contents = pd.read_csv(os.path.join(data_dir, "contents.csv"), index_col=0)
    metadata = pd.read_csv(os.path.join(data_dir, "metadata.csv"), index_col=0)
    metadata["created_at"] = pd.to_datetime(metadata.created_at)
    contributions = pd.read_csv(os.path.join(data_dir, "contributions.csv"), index_col=0)
    contributions["week_co"] = pd.to_datetime(contributions.week_co)
    readme_df = pd.read_csv(os.path.join(data_dir, "readme_history.csv"), index_col=0)
    stars = pd.read_csv(os.path.join(data_dir, "stars.csv"), index_col=0)
    forks = pd.read_csv(os.path.join(data_dir, "forks.csv"), index_col=0)

    if filter_path is not None:  # e.g. filter for high-interest repositories based on a txt file containing a list of those
        info(verbose, "Filtering data...")
        with open(filter_path, "r") as f:
            filtered = [line.rstrip() for line in f]
        contents = contents.loc[contents.github_user_cleaned_url.isin(filtered)]
        metadata = metadata.loc[metadata.github_user_cleaned_url.isin(filtered)]
        contributions = contributions.loc[contributions.github_user_cleaned_url.isin(filtered)]
        readme_df = readme_df.loc[readme_df.github_user_cleaned_url.isin(filtered)]
        stars = stars.loc[stars.github_user_cleaned_url.isin(filtered)]
        forks = forks.loc[forks.github_user_cleaned_url.isin(filtered)]

    info(verbose, "Plotting...")
    fig = plt.figure(figsize=(20, 15))
    ax5 = plt.subplot(8, 5, (26, 38))
    ax4 = plt.subplot(8, 5, (16, 23), sharex=ax5)
    ax1 = plt.subplot(8, 5, (1, 13), sharex=ax5)
    ax3 = plt.subplot(8, 5, (4, 15))
    ax6 = plt.subplot(8, 5, (19, 30))
    ax7 = plt.subplot(8, 5, (34, 40))
    fig.tight_layout(h_pad=0.5, w_pad=3, rect=(0.05, 0.05, 0.95, 0.95))
    plot_license_type(contents, ax1)
    plot_contributing_file_present(contents, ax4)
    plot_team_size(metadata, contributions, ax5)
    plot_readme_size(contents, ax3, type="pie")
    plot_headings(readme_df, ax6)
    plot_table(metadata, stars, forks, ax7)
    if tag:
        plt.suptitle(f"Overall statistics for ePrints repositories ({tag})")
        plt.savefig(os.path.join(outdir, "plots", "overall", f"overall_reduced_{tag}.png"), bbox_inches="tight", transparent=True)
    else:
        plt.suptitle("Overall statistics for ePrints repositories")
        plt.savefig(os.path.join(outdir, "plots", "overall", "overall_reduced.png"), bbox_inches="tight", transparent=True)

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="overall",
        description="Plot overall repo analysis."
    )
    parser.add_argument("--datadir", default="../../data/raw/github", type=str, help="path to GitHub data directory")
    parser.add_argument("--outdir", default="../../data/derived", type=str, help="path to output data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    parser.add_argument("--filter", type=str, help="path to file listing the repos that should be considered")
    parser.add_argument("--tag", type=str, help="tag to add to the filename, e.g. to indicate that the repositories were filtered")
    args = parser.parse_args()
    main(args.datadir, args.outdir, args.verbose, args.filter, args.tag)
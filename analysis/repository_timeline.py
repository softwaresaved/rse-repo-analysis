import argparse
import pandas as pd
import numpy as np
import os
import seaborn as sns
from datetime import datetime, timezone
from matplotlib import pyplot as plt

def info(verbose, msg):
    if verbose:
        print(f"[INFO] {msg}")

def load_data(data_dir, filename, repo, to_datetime=None):
    df = pd.read_csv(os.path.join(data_dir, filename), index_col=0)
    df = df[df["github_user_cleaned_url"] == repo]
    if type(to_datetime) == list:
        for dt in to_datetime:
            df[dt] = pd.to_datetime(df[dt], utc=True)
    elif type(to_datetime) == str:
        df[to_datetime] = pd.to_datetime(df[to_datetime], utc=True)
    return df

def analyse_headings(df):
    interesting_words = {
        "ownership": ["license", "example", "reference", "citation", "cited", "publication", "paper"],
        "usage": ["requirements", "using", "example", "usage", "run", "install", "installing", "installation", "tutorial", "tutorials", "build", "guide", "documentation"]
    }
    df["ownership_addition"] = df.added_headings.str.contains("|".join(interesting_words["ownership"]), case=False)
    df["usage_addition"] = df.added_headings.str.contains("|".join(interesting_words["usage"]), case=False)
    return df

def engagement_user_highlights(users, metadata, forks, stars, ax):
    user_forks = pd.merge(forks[forks.user.isin(users)], metadata, on="github_user_cleaned_url")
    user_forks["week_since_repo_creation"] = (user_forks.date - user_forks.created_at).dt.days // 7
    user_stars = pd.merge(stars[stars.user.isin(users)], metadata, on="github_user_cleaned_url")
    user_stars["week_since_repo_creation"] = (user_stars.date - user_stars.created_at).dt.days // 7
    ax.scatter(user_forks.week_since_repo_creation, user_forks.user, marker="v", s=100, label="forked")
    ax.scatter(user_stars.week_since_repo_creation, user_stars.user, marker="v", s=100, label="starred")

def user_type_wrt_issues(issues, metadata, forks, stars, ax):
    # map dates to weeks
    merged_df = pd.merge(issues, metadata, on="github_user_cleaned_url", suffixes=(None,"_repo"))
    merged_df["created_at"] = (merged_df["created_at"] - merged_df["created_at_repo"]).dt.days // 7
    merged_df["closed_at"] = (merged_df["closed_at"] - merged_df["created_at_repo"]).dt.days // 7
    # count number of created and closed issues by user + week
    created = merged_df.groupby(["user", "created_at"])["state"].count().rename("created_count")
    created.index.rename({"created_at": "week_since_repo_creation"}, inplace=True)
    closed = merged_df.groupby(["closed_by", "closed_at"])["state"].count().rename("closed_count")
    closed.index.rename({"closed_at": "week_since_repo_creation", "closed_by": "user"}, inplace=True)
    issues_by_user = pd.merge(created, closed, left_index=True, right_index=True, how="outer")
    # build timeline DataFrame
    end = (datetime.now(tz=timezone.utc) - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    df = pd.merge(x_data, pd.Series(issues_by_user.index.unique(level="user")), how="cross").set_index(["user", "week_since_repo_creation"])
    df = pd.merge(df, issues_by_user, left_index=True, right_index=True, how="outer")
    df.fillna(0, inplace=True)
    # determine user status with window of 12 weeks onwards
    windowed_df = df.groupby(level="user").rolling(window=12, min_periods=0).sum().droplevel(0)
    conditions = [(windowed_df.created_count > 0) & (windowed_df.closed_count == 0), (windowed_df.created_count == 0) & (windowed_df.closed_count > 0), (windowed_df.created_count > 0) & (windowed_df.closed_count > 0)]
    choices = ["opening", "closing", "both"]
    windowed_df["status"] = np.select(conditions, choices, default="inactive")
    # plot
    sns.scatterplot(
        ax=ax,
        data=windowed_df,
        x="week_since_repo_creation",
        y="user",
        hue="status",
        hue_order=["inactive", "opening", "closing", "both"],
        palette=['#d62728', '#1f77b4', '#ff7f0e', '#2ca02c'],
        marker="|",
        s=500,
        )
    ax.set_ylabel("issue user")
    users = np.unique(np.concatenate([issues.user.unique(), issues.closed_by.dropna().unique()]))
    engagement_user_highlights(users, metadata, forks, stars, ax)

def contributor_team(contributions, metadata, forks, stars, axs):
    # map dates to weeks
    contrib_df = pd.merge(metadata[["github_user_cleaned_url", "created_at"]], contributions)
    contrib_df["week_since_repo_creation"] = (contrib_df.week_co - contrib_df.created_at).dt.days // 7
    team_df = contrib_df[["author", "week_since_repo_creation", "commits"]].set_index(["author", "week_since_repo_creation"]).sort_index()
    # user is active contributor if made at least one commit in last 12 weeks
    windowed_team_df = team_df.groupby(level="author").rolling(window=12, min_periods=0).sum().droplevel(0)
    windowed_team_df["active contributors"] = windowed_team_df.commits > 0
    # plot per-user status
    sns.scatterplot(
        ax=axs[0],
        data=windowed_team_df,
        x="week_since_repo_creation",
        y="author",
        hue="active contributors",
        hue_order=[False, True],
        palette=['#d62728', '#2ca02c'],
        marker="|",
        s=500,
    )
    axs[0].set_ylabel("contributing user")
    users = contributions.author.unique()
    engagement_user_highlights(users, metadata, forks, stars, axs[0])
    # team size
    team_size = windowed_team_df.groupby(level="week_since_repo_creation")["active contributors"].value_counts()[:,True].reindex(windowed_team_df.index.levels[1], fill_value=0)
    # plot
    team_size.plot(
        ax=axs[1],
        color="black",
        lw=2,
        # xlabel="week since repo creation",
        # ylabel="contributor team size",
    )

def no_open_and_closed_issues(issues, metadata, ax):
    # reframe timeline in terms of week since repo creation
    issues_timeline_df = pd.merge(metadata, issues, on="github_user_cleaned_url", suffixes=("_repo", None))
    issues_timeline_df["opened_in_week_since_repo_creation"] = (issues_timeline_df.created_at - issues_timeline_df.created_at_repo).dt.days // 7
    issues_timeline_df["closed_in_week_since_repo_creation"] = (issues_timeline_df.closed_at - issues_timeline_df.created_at_repo).dt.days // 7
    # build weekly dataframe
    end = (datetime.now(tz=timezone.utc) - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    issue_count_timeline = pd.DataFrame(x_data)
    # count issues
    issue_count_timeline["open_issues_count"] = issue_count_timeline.apply(lambda x: len(issues_timeline_df[
                                                                                            (issues_timeline_df.opened_in_week_since_repo_creation <= x.week_since_repo_creation) &
                                                                                            (issues_timeline_df.closed_in_week_since_repo_creation >= x.week_since_repo_creation)
                                                                                            ]), axis=1)
    issue_count_timeline["closed_issues_count"] = issue_count_timeline.apply(lambda x: len(issues_timeline_df[
                                                                                            (issues_timeline_df.closed_in_week_since_repo_creation < x.week_since_repo_creation)
                                                                                            ]), axis=1)
    # plot
    issue_count_timeline.rename(columns={"open_issues_count": "open issues", "closed_issues_count": "closed issues"}).plot(
        ax=ax,
        x="week_since_repo_creation",
        y=["open issues", "closed issues"],
        lw=2,
        # xlabel="week since repo creation",
        # ylabel="count"
        )
    
def engagement(forks, stars, metadata, ax):
    forks_df = pd.merge(forks, metadata, on="github_user_cleaned_url")
    forks_df["week_since_repo_creation"] = (forks_df.date - forks_df.created_at).dt.days // 7
    forks_df = forks_df[["week_since_repo_creation", "user"]].groupby("week_since_repo_creation").count().rename(columns={"user": "no forks"}).sort_index()
    stars_df = pd.merge(stars, metadata, on="github_user_cleaned_url")
    stars_df["week_since_repo_creation"] = (stars_df.date - stars_df.created_at).dt.days // 7
    stars_df = stars_df[["week_since_repo_creation", "user"]].groupby("week_since_repo_creation").count().rename(columns={"user": "no stars"}).sort_index()
    end = (datetime.now(tz=timezone.utc) - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    engagement_df = pd.merge(x_data, forks_df, on="week_since_repo_creation", how="outer")
    engagement_df = pd.merge(engagement_df, stars_df, on="week_since_repo_creation", how="outer").fillna(0)
    engagement_df = engagement_df.set_index("week_since_repo_creation")
    engagement_df = engagement_df.cumsum()
    engagement_df.plot(
        ax=ax,
        lw=2
    )
    
def date_highlights(readme_history, contents, metadata, paper_data, ax):
    df = pd.merge(metadata, readme_history, on="github_user_cleaned_url")
    df.dropna(subset=["author_date"], inplace=True)
    df["authored_in_week_since_creation"] = (df.author_date - df.created_at).dt.days // 7
    contents_df = pd.merge(metadata, contents, on="github_user_cleaned_url")
    contents_df.citation_added = (contents_df.citation_added - contents_df.created_at).dt.days // 7
    contents_df.contributing_added = (contents_df.contributing_added - contents_df.created_at).dt.days // 7
    paper_df = pd.merge(metadata, paper_data, on="github_user_cleaned_url")
    paper_df.date = (paper_df.date - paper_df.created_at).dt.days // 7
    # headings
    df = analyse_headings(df)
    # plotting
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    max_y = ax.get_ylim()[1]
    dist = max_y/25
    ownership_added = df[df.ownership_addition].authored_in_week_since_creation
    ax.vlines(ownership_added, -1*dist, max_y, linestyles='dashed', color=colors[0])
    ax.scatter(ownership_added, (-1*dist * np.ones((len(ownership_added),))), marker=10, s=100, label="ownership heading", color=colors[0])
    usage_added = df[df.usage_addition].authored_in_week_since_creation
    ax.vlines(usage_added, -2*dist, max_y, linestyles='dashed', color=colors[1])
    ax.scatter(usage_added, (-2*dist * np.ones((len(usage_added),))), marker=10, s=100, label="usage heading", color=colors[1])
    # citation in README
    citation_added = df[(df.added_cites != "[]") & (df.added_cites.notna())].authored_in_week_since_creation
    ax.vlines(citation_added, -3*dist, max_y, linestyles='dashed', color=colors[2])
    ax.scatter(citation_added, (-3*dist * np.ones((len(citation_added),))), marker=10, s=100, label="citation in README", color=colors[2])
    # citation file
    citation_file_added = contents_df[contents_df.citation_added.notna()].citation_added
    ax.vlines(citation_file_added, -4*dist, max_y, linestyles='dashed', color=colors[3])
    ax.scatter(citation_file_added, (-4*dist* np.ones((len(citation_file_added),))), marker=10, s=100, label="citation file", color=colors[3])
    # contributing file
    contributing_file_added = contents_df[contents_df.contributing_added.notna()].contributing_added
    ax.vlines(contributing_file_added, -5*dist, max_y, linestyles='dashed', color=colors[4])
    ax.scatter(contributing_file_added, (-5*dist* np.ones((len(contributing_file_added),))), marker=10, s=100, label="contributing file", color=colors[4])
    # paper publication
    paper_published = paper_df[paper_df.date.notna()].date
    ax.vlines(paper_published, -6*dist, max_y, linestyles='dashed', color=colors[5])
    ax.scatter(paper_published, (-6*dist* np.ones((len(paper_published),))), marker=10, s=100, label="mention in publication", color=colors[5])

def main(repo, dir, output_dir, verbose):
    info(verbose, f"Loading data for repo {repo}...")
    contents = load_data(dir, "contents.csv", repo, ["citation_added", "contributing_added"])
    contributions = load_data(dir, "contributions.csv", repo, "week_co")
    forks = load_data(dir, "forks.csv", repo, "date")
    issues = load_data(dir, "issues.csv", repo, ["created_at", "closed_at"])
    metadata = load_data(dir, "metadata.csv", repo, "created_at")
    readme_history = load_data(dir, "readme_history.csv", repo, "author_date")
    stars = load_data(dir, "stars.csv", repo, "date")
    paper_data = load_data(os.path.join(dir, "cleaned_links"), "joined.csv", repo, "date")
    info(verbose, "Data loading complete.")

    if len(metadata) == 0:
        info(verbose, f"Not enough data available for {repo}.")
        exit()

    fig, axs = plt.subplots(nrows=3, figsize=(20, 10), sharex=True)
    info(verbose, "Crunching data...")
    user_type_wrt_issues(issues, metadata, forks, stars, axs[0])
    axs[0].legend(loc="upper right")
    axs[0].grid(True, axis="x")
    contributor_team(contributions, metadata, forks, stars, axs[1:])
    axs[1].grid(True, axis="x")
    axs[1].legend()
    no_open_and_closed_issues(issues, metadata, axs[2])
    engagement(forks, stars, metadata, axs[2])
    date_highlights(readme_history, contents, metadata, paper_data, axs[2])
    axs[2].legend(loc="upper right")
    axs[2].grid(True)
    _, right = plt.xlim()
    plt.xlim(-5, right+15)
    plt.xlabel("week since repository creation")
    fig.suptitle(repo)
    s = repo.replace("/", "-")
    fig.tight_layout()
    outpath = os.path.join(dir, output_dir)
    os.makedirs(outpath, exist_ok=True)
    plt.savefig(os.path.join(outpath, f"{s}.png"), bbox_inches="tight")
    info(verbose, f"Plot saved in {outpath}, file {s}.png.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="repository_timeline",
        description="Plot repository events and development on timeline."
    )
    parser.add_argument("--repo", required=True, type=str, help="GitHub ID")
    parser.add_argument("--dir", default="../data/analysis", type=str, help="path to data directory")
    parser.add_argument("--outdir", default="repo_timelines/true_positives", type=str, help="name of output folder in data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.repo, args.dir, args.outdir, args.verbose)
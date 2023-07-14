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

def user_type_wrt_issues(issues, metadata, ax):
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

def contributor_team_size(contributions, metadata, ax):
    team_df = pd.merge(metadata[["github_user_cleaned_url", "created_at"]], contributions)
    team_df["week_since_repo_creation"] = (team_df.week_co - team_df.created_at).dt.days // 7
    # determine team membership for each week based on having commited at least once in the last 12 weeks
    windowed_commits = team_df.groupby(["author"]).rolling(window=12, min_periods=0).commits.sum()
    team_df["windowed_commits"] = windowed_commits.droplevel(0)
    team_df["is_team_member"] = team_df.windowed_commits > 0
    team_size = team_df.groupby(["week_since_repo_creation"]).is_team_member.value_counts().rename("contributor team size")[:,True].reindex(
        team_df.week_since_repo_creation.unique(), fill_value=0)  # reindex to get weeks where the count is 0
    # plot
    team_size.plot(
        ax=ax,
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
        # xlabel="week since repo creation",
        # ylabel="count"
        )
    
def date_highlights(readme_history, contents, metadata, ax):
    df = pd.merge(metadata, readme_history, on="github_user_cleaned_url")
    df.dropna(subset=["author_date"], inplace=True)
    df["authored_in_week_since_creation"] = (df.author_date - df.created_at).dt.days // 7
    # headings
    df = analyse_headings(df)
    ownership_added = df[df.ownership_addition].authored_in_week_since_creation
    ax.scatter(ownership_added, (-2 * np.ones((len(ownership_added),))), marker="v", label="ownership heading")
    usage_added = df[df.usage_addition].authored_in_week_since_creation
    ax.scatter(usage_added, (-1 * np.ones((len(usage_added),))), marker="v", label="usage heading")
    # citation in README
    citation_added = df[(df.added_cites != "[]") & (df.added_cites.notna())]
    ax.scatter(citation_added, (-3 * np.ones((len(citation_added),))), marker="v", label="citation in README")

def main(repo, dir, verbose):
    info(verbose, "Loading data...")
    contents = load_data(dir, "contents.csv", repo, "citation_added")
    contributions = load_data(dir, "contributions.csv", repo, "week_co")
    forks = load_data(dir, "forks.csv", repo, "date")
    issues = load_data(dir, "issues.csv", repo, ["created_at", "closed_at"])
    metadata = load_data(dir, "metadata.csv", repo, "created_at")
    readme_history = load_data(dir, "readme_history.csv", repo, "author_date")
    stars = load_data(dir, "stars.csv", repo, "date")
    info(verbose, "Data loading complete.")

    fig, axs = plt.subplots(nrows=2, figsize=(20, 10), sharex=True)
    info(verbose, "Crunching data...")
    user_type_wrt_issues(issues, metadata, axs[0])
    axs[0].legend(loc="upper right")
    contributor_team_size(contributions, metadata, axs[1])
    no_open_and_closed_issues(issues, metadata, axs[1])
    date_highlights(readme_history, contents, metadata, axs[1])
    _, right = plt.xlim()
    plt.xlim(0, right+10)
    axs[1].legend(loc="upper right")
    fig.suptitle(repo)
    s = repo.replace("/", "-")
    output_dir = "repo_timelines"
    os.makedirs(os.path.join(dir, output_dir), exist_ok=True)
    plt.savefig(os.path.join(dir, output_dir, f"{s}.png"), bbox_inches="tight")
    info(verbose, "Plot saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="repository_timeline",
        description="Plot repository events and development on timeline."
    )
    parser.add_argument("--repo", required=True, type=str, help="GitHub ID")
    parser.add_argument("--dir", default="../data/analysis", type=str, help="path to data directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.repo, args.dir, args.verbose)
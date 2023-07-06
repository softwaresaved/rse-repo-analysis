import argparse
import pandas as pd
import numpy as np
import os
from datetime import datetime
from matplotlib import pyplot as plt

def info(verbose, msg):
    if verbose:
        print(f"[INFO] {msg}")

def load_data(data_dir, filename, repo, to_datetime=None):
    df = pd.read_csv(os.path.join(data_dir, filename), index_col=0)
    df = df[df["github_user_cleaned_url"] == repo]
    if type(to_datetime) == list:
        for dt in to_datetime:
            df[dt] = pd.to_datetime(df[dt])
    elif type(to_datetime) == str:
        df[to_datetime] = pd.to_datetime(df[to_datetime])
    return df

def determine_user_type_for_week(row):
    margin = 12
    status = "inactive"
    if row.week_since_repo_creation >= row.created_at_first and row.week_since_repo_creation <= (row.created_at_last + margin):
        status = "opening"
        if row.week_since_repo_creation >= row.closed_at_first and row.week_since_repo_creation <= (row.closed_at_last + margin):
            status = "both"
    elif row.week_since_repo_creation >= row.closed_at_first and row.week_since_repo_creation <= (row.closed_at_last + margin):
        status = "closing"
    row["status"] = status
    return row

def user_type_wrt_issues(issues, metadata, ax):
    # calculate week since repo creation that issue was created or closed in
    first = issues.groupby(["user", "github_user_cleaned_url"])[["created_at", "closed_at"]].min()
    last = issues.groupby(["user", "github_user_cleaned_url"])[["created_at", "closed_at"]].max()
    issue_dates = pd.merge(first, last, on=["user", "github_user_cleaned_url"], suffixes=["_first", "_last"]).reset_index()
    issue_dates = pd.merge(issue_dates, metadata[["github_user_cleaned_url", "created_at"]], on="github_user_cleaned_url")
    for col in ["created_at_first", "closed_at_first", "created_at_last", "closed_at_last"]:
        issue_dates[col] = (issue_dates[col] - issue_dates["created_at"]).dt.days // 7
    # build weekly dataframe
    end = (datetime.today() - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    df = pd.merge(x_data, issue_dates, how="cross")
    # map user type
    df = df.apply(determine_user_type_for_week, axis=1)
    issue_user_types = df.groupby(["week_since_repo_creation", "status"])["user"].count().unstack()
    ordered_categories = ["inactive", "opening", "closing", "both"]
    issue_user_types.columns = pd.CategoricalIndex(
        issue_user_types.columns.values,
        ordered=True,
        categories=ordered_categories)
    issue_user_types.sort_index(axis=1, inplace=True)
    # plot
    issue_user_types.plot.bar(
        stacked=True,
        ax = ax,
        xlabel="week since repo creation",
        ylabel="user count",
        #legend="reverse",
        color=['#d62728', '#1f77b4', '#ff7f0e', '#2ca02c']
        #colormap="RdYlGn"
    )
    ax.set_xticks(ax.get_xticks()[::10])

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
    end = (datetime.today() - metadata.created_at.iloc[0]).days // 7
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

    fig, axs = plt.subplots(nrows=2, figsize=(20, 10))
    info(verbose, "Crunching data...")
    user_type_wrt_issues(issues, metadata, axs[0])
    contributor_team_size(contributions, metadata, axs[0])
    axs[0].legend()
    no_open_and_closed_issues(issues, metadata, axs[1])
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
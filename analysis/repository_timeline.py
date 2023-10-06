import argparse
import pandas as pd
import numpy as np
import os
import seaborn as sns
from datetime import datetime, timezone, timedelta
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

def user_type_wrt_issues(issues, metadata, forks, stars, analysis_end_date, ax):
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
    end = (analysis_end_date - metadata.created_at.iloc[0]).days // 7
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
    windowed_team_df["active contributors"] = windowed_team_df["active contributors"].map({True: "active", False: "inactive"})
    # plot per-user status
    sns.scatterplot(
        ax=axs[0],
        data=windowed_team_df,
        x="week_since_repo_creation",
        y="author",
        hue="active contributors",
        hue_order=["inactive", "active"],
        palette=['#d62728', '#2ca02c'],
        marker="|",
        s=500,
    )
    axs[0].set_ylabel("contributing user")
    users = contributions.author.unique()
    engagement_user_highlights(users, metadata, forks, stars, axs[0])
    # team size
    team_size = windowed_team_df.groupby(level="week_since_repo_creation")["active contributors"].value_counts()[:,"active"].reindex(windowed_team_df.index.levels[1], fill_value=0)
    # plot
    team_size.plot(
        ax=axs[1],
        lw=2,
        # xlabel="week since repo creation",
        ylabel="number of contributors",
    )
    # overall pool of contributors
    contributor_pool_df = team_df.groupby(level="author").cumsum()
    contributor_pool_df["contributors"] = contributor_pool_df.commits > 0
    contrib_pool = contributor_pool_df.groupby(level="week_since_repo_creation")["contributors"].value_counts()[:,True].reindex(contributor_pool_df.index.levels[1], fill_value=0)
    contrib_pool.plot(
        ax=axs[1],
        lw=2,
    )

def no_open_and_closed_issues(issues, metadata, analysis_end_date, ax):
    # reframe timeline in terms of week since repo creation
    issues_timeline_df = pd.merge(metadata, issues, on="github_user_cleaned_url", suffixes=("_repo", None))
    issues_timeline_df["opened_in_week_since_repo_creation"] = (issues_timeline_df.created_at - issues_timeline_df.created_at_repo).dt.days // 7
    issues_timeline_df["closed_in_week_since_repo_creation"] = (issues_timeline_df.closed_at - issues_timeline_df.created_at_repo).dt.days // 7
    # build weekly dataframe
    end = (analysis_end_date - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    issue_count_timeline = pd.DataFrame(x_data)
    # count issues
    issue_count_timeline["open_issues_count"] = issue_count_timeline.apply(lambda x: len(issues_timeline_df[
                                                                                            (issues_timeline_df.opened_in_week_since_repo_creation <= x.week_since_repo_creation) &
                                                                                            ((issues_timeline_df.closed_in_week_since_repo_creation >= x.week_since_repo_creation) |
                                                                                             (issues_timeline_df.closed_in_week_since_repo_creation.isna()))
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
        ylabel="issue count"
        )
    
def engagement(forks, stars, metadata, analysis_end_date, ax):
    forks_df = pd.merge(forks, metadata, on="github_user_cleaned_url")
    forks_df["week_since_repo_creation"] = (forks_df.date - forks_df.created_at).dt.days // 7
    forks_df = forks_df[["week_since_repo_creation", "user"]].groupby("week_since_repo_creation").count().rename(columns={"user": "no forks"}).sort_index()
    stars_df = pd.merge(stars, metadata, on="github_user_cleaned_url")
    stars_df["week_since_repo_creation"] = (stars_df.date - stars_df.created_at).dt.days // 7
    stars_df = stars_df[["week_since_repo_creation", "user"]].groupby("week_since_repo_creation").count().rename(columns={"user": "no stars"}).sort_index()
    end = (analysis_end_date - metadata.created_at.iloc[0]).days // 7
    x_data = pd.Series(np.arange(end), name="week_since_repo_creation")
    engagement_df = pd.merge(x_data, forks_df, on="week_since_repo_creation", how="outer")
    engagement_df = pd.merge(engagement_df, stars_df, on="week_since_repo_creation", how="outer").fillna(0)
    engagement_df = engagement_df.set_index("week_since_repo_creation")
    engagement_df = engagement_df.cumsum()
    engagement_df.plot(
        ax=ax,
        lw=2,
        ylabel="count"
    )
    
def calc_y_timeline(data):
    ys = [[] for _ in range(len(data))]
    seen_x = []
    for i in range(len(data)):
        for x in data[i]:
            ys[i].append(-1 * seen_x.count(x))
            seen_x.append(x)
    return ys

def date_highlights(readme_history, contents, metadata, paper_data, ax, overlay_ax):
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
    ownership_added = df[df.ownership_addition].authored_in_week_since_creation
    usage_added = df[df.usage_addition].authored_in_week_since_creation
    # citation in README
    citation_added = df[(df.added_cites != "[]") & (df.added_cites.notna())].authored_in_week_since_creation
    # citation file
    citation_file_added = contents_df[contents_df.citation_added.notna()].citation_added
    # contributing file
    contributing_file_added = contents_df[contents_df.contributing_added.notna()].contributing_added
    # paper publication
    paper_published = paper_df[paper_df.date.notna()].date
    # plotting
    ax.set(ylim=(-6, 0.4), yticks=[])
    ax.set_xlabel("weeks since repository creation", loc="right")
    ax.xaxis.set_label_position('top')
    ax.xaxis.tick_top()
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    data = [ownership_added, usage_added, citation_added, citation_file_added, contributing_file_added, paper_published]
    ys = calc_y_timeline(data)
    labels = ["ownership heading", "usage heading", "citation in README", "citation file", "contributing file", "mention in publication"]
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    ymax = 86
    for i in range(len(data)):
        ax.scatter(data[i], ys[i], marker="^", s=100, label=labels[i], color=colors[i])
        overlay_ax.vlines(data[i], ys[i], ymax, linestyles='dashed', color=colors[i])

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

    analysis_end_date = contributions.week_co.max() + timedelta(days=7)

    if len(metadata) == 0:
        info(verbose, f"Not enough data available for {repo}.")
        exit()

    fig = plt.figure(figsize=(20, 20))
    overlay_axis = fig.subplots()
    overlay_axis.axis('off')
    axs = fig.subplots(nrows=6, sharex=True, height_ratios=[3, 3, 2, 2, 2, 1])
    for ax in axs:
        ax.patch.set_alpha(0)
    info(verbose, "Crunching data...")
    user_type_wrt_issues(issues, metadata, forks, stars, analysis_end_date, axs[0])
    axs[0].legend(loc="upper right")
    axs[0].grid(True, axis="x")
    contributor_team(contributions, metadata, forks, stars, axs[1:3])
    axs[1].grid(True, axis="x")
    axs[1].legend()
    axs[2].legend(loc="upper right")
    axs[2].grid(True)
    no_open_and_closed_issues(issues, metadata, analysis_end_date, axs[3])
    axs[3].legend(loc="upper right")
    axs[3].grid(True)
    engagement(forks, stars, metadata, analysis_end_date, axs[4])
    axs[4].legend(loc="upper right")
    axs[4].grid(True)    
    date_highlights(readme_history, contents, metadata, paper_data, axs[5], overlay_axis)
    axs[5].legend(loc="upper right", ncols=2)
    # final adjustments
    ymax = 86
    xl, xr = plt.xlim()
    plt.xlim(xl, xr+15)
    overlay_axis.set(xlim=(xl, xr+15), ylim=(-6, ymax))
    fig.suptitle(repo)
    s = repo.replace("/", "-")
    fig.tight_layout(rect=[0, 0.03, 1, 0.98])
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
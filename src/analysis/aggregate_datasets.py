# TODO: remove unused
import pandas as pd
import numpy as np
import os
import argparse
import ast
import string
import re
import os
from datetime import datetime, timezone, timedelta

def info(verbose, msg):
    """Print message to stdout if verbose is True.

    Args:
        verbose (bool): if True, print message.
        msg (str): debugging message
    """
    if verbose:
        print(f"[INFO] {msg}")

def license_type(contents):
    """Categorise license into permissive, non-permissive, none and unknown.

    Args:
        contents (pd.DataFrame): dataframe with column "license".

    Returns:
        pd.DataFrame: same dataframe with added column "license_type".
    """
    contents = contents.copy()
    permissive_licenses = ["mit", "gpl-3.0", "apache-2.0", "bsd-3-clause", "gpl-2.0", "bsd-2-clause"] # https://en.wikipedia.org/wiki/Permissive_software_license
    contents.license = contents.license.fillna('None')
    # TODO: refactor with np.select?
    contents["license_type"] = np.where(
        contents.license.isin(permissive_licenses), "permissive", np.where(
        contents.license == "None", "None", np.where(
        contents.license == "other", "unknown", "non-permissive")))
    return contents

def team_size(contributions):
    """Count the number of (active) contributors for each repository over time. A user is an active contributor if they made at least one commit in last 12 weeks.

    Args:
        contributions (pd.DataFrame): dataframe with GitHub commit data

    Returns:
        pd.DataFrame: data frame where each row corresponds to one week in a repo's life and includes the number of active contributors and overall contributors
    """
    team_df = contributions[["github_user_cleaned_url", "author", "week_since_repo_creation_week_co", "commits"]].set_index(["github_user_cleaned_url", "author", "week_since_repo_creation_week_co"]).sort_index()
    # user is active contributor if made at least one commit in last 12 weeks
    windowed_team_df = team_df.groupby(level=["github_user_cleaned_url", "author"]).rolling(window=12, min_periods=0).sum().droplevel([0, 1])
    final_index = windowed_team_df.index.droplevel(1).unique()
    windowed_team_df["active_contributors"] = windowed_team_df.commits > 0
    # contributor team size
    contrib_team_size = windowed_team_df.groupby(level=["github_user_cleaned_url", "week_since_repo_creation_week_co"])["active_contributors"].value_counts()[:,:,True].reindex(final_index, fill_value=0).astype(int)
    # overall pool of contributors
    contributor_pool_df = team_df.groupby(["github_user_cleaned_url", "author"]).cumsum()
    contributor_pool_df["contributors"] = contributor_pool_df.commits > 0
    contrib_pool = contributor_pool_df.groupby(level=["github_user_cleaned_url", "week_since_repo_creation_week_co"])["contributors"].value_counts()[:,:,True].reindex(final_index, fill_value=0).astype(int)
    contributors_df = pd.merge(contrib_team_size, contrib_pool, left_index=True, right_index=True)
    contributors_df.index.rename({"week_since_repo_creation_week_co": "week_since_repo_creation"}, inplace=True)
    return contributors_df

def readme_size_classification(contents):
    """Classify the amount of detail in a README file based on its size. Thresholds were determined empirically.

    Args:
        contents (pd.DataFrame): dataframe with column "readme_size"

    Returns:
        pd.DataFrame: same dataframe with added column "readme_size_class".
    """
    def map_size(byte_size):  # TODO: refactor with np.select?
        if byte_size < 1:
            return "none"
        if byte_size < 300:
            return "ultra-short"
        if byte_size < 1500:
            return "short"
        if byte_size < 10000:
            return "informative"
        else:  # larger than 10000 Bytes
            return "detailed"
    contents["readme_size_class"] = contents.readme_size.map(map_size)
    return contents

def load_data(data_dir, filename, to_datetime=None):
    """Load dataframes from file and convert relevant dolumns to datetime type.

    Args:
        data_dir (str): path to data folder
        filename (str): name of data file
        to_datetime (list<str> | str, optional): Columns that should be converted to datetime. Defaults to None.

    Returns:
        pd.DataFrame: modified data frame
    """
    df = pd.read_csv(os.path.join(data_dir, filename), index_col=0)
    if type(to_datetime) == list:
        for dt in to_datetime:
            df[dt] = pd.to_datetime(df[dt], utc=True)
    elif type(to_datetime) == str:
        df[to_datetime] = pd.to_datetime(df[to_datetime], utc=True)
    return df

def aggregate_week_since_repo_creation(metadata, df, label=None):
    """Translate date columns into weeks since repo creation.

    Args:
        metadata (pd.DataFrame): dataframe with columns "github_user_cleaned_url" and "created_at"
        df (pd.DataFrame): dataframe that should be aggregated
        label (list<str> | str, optional): column name(s) with date information

    Returns:
        pd.DataFrame: input dataframe with added column "week_since_repo_creation_{original_column_name}"
    """
    repo_creation_df = metadata[["created_at", "github_user_cleaned_url"]].rename(columns={"created_at": "repo_created_at"})
    df = pd.merge(df, repo_creation_df, on="github_user_cleaned_url")
    if type(label) == list:
        for column in label:
            df[f"week_since_repo_creation_{column}"] = (df[column] - df.repo_created_at).dt.days // 7
    elif type(label) == str:
        df[f"week_since_repo_creation_{label}"] = (df[label] - df.repo_created_at).dt.days // 7
    return df

def filter_repo(df, repo):
    """Choose subset of dataframe that deals with a specific GitHub repository.

    Args:
        df (pd.DataFrame): dataframe with column "github_user_cleaned_url"
        repo (str): GitHub repository ID

    Returns:
        pd.DataFrame: input dataframe with only the columns for the given repo.
    """
    return df[df["github_user_cleaned_url"] == repo]

def clean_headings(readme_df):
    """Remove digits (e.g. heading or version numbering) from headings, convert to lowercase.

    Args:
        readme_df (pd.DataFrame): dataframe with README history, including columns "added_headings" and "deleted_headings"

    Returns:
        pd.DataFrame: input dataframe with additional columns "cleaned_added_headings" and "cleaned_deleted_headings"
    """
    def clean(headings_list):
        l = ast.literal_eval(headings_list)
        to_remove = string.digits + string.whitespace + ".:"
        cleaned_headings_list = []
        for h in l:
            h = h.lstrip(to_remove)
            # remove markdown-style links
            pattern = r"\[(.+?)\]\(.+?\)"
            h = re.sub(pattern, r'\1', h, count=0)
            h = h.replace(string.punctuation, "")
            h = h.strip(string.punctuation)
            h = h.lower()
            cleaned_headings_list.append(h)
        return cleaned_headings_list
    readme_df["cleaned_added_headings"] = readme_df.added_headings.map(clean, na_action="ignore")
    readme_df["cleaned_deleted_headings"] = readme_df.deleted_headings.map(clean, na_action="ignore")
    return readme_df

def engagement_counts(stars, forks):
    """Count forks and stars for each repository

    Args:
        stars (pd.DataFrame): dataframe with columns "github_user_cleaned_url" and "user" for each added fork
        forks (pd.DataFrame): dataframe with columns "github_user_cleaned_url" and "user" for each added star

    Returns:
        pd.DataFrame: dataframe with columns "github_user_cleaned_url", "stars_count", "forks_count"
    """
    fork_counts = forks.groupby("github_user_cleaned_url")["user"].count()
    fork_counts.rename("forks_count", inplace=True)
    star_counts = stars.groupby("github_user_cleaned_url")["user"].count()
    star_counts.rename("stars_count", inplace=True)
    engagement_df = pd.concat([fork_counts, star_counts], axis=1).reset_index()
    return engagement_df    

############## timeline

def analyse_headings(df):
    """Map added headings to relevant ownership and usage vocabulary. Vocabulary is constructed based on empirical findings so will likely not be complete.

    Args:
        df (pd.DataFrame): dataframe with column "added_headings"

    Returns:
        pd.DataFrame: same dataframe with added boolean columns "ownership_addtion" and "usage_addition"
    """
    interesting_words = {
        "ownership": ["license", "example", "reference", "citation", "cited", "publication", "paper"],
        "usage": ["requirements", "using", "example", "usage", "run", "install", "installing", "installation", "tutorial", "tutorials", "build", "guide", "documentation"]
    }
    df = df.fillna(value={"added_headings": ""})
    df["ownership_addition"] = df.added_headings.str.contains("|".join(interesting_words["ownership"]), case=False)
    df["usage_addition"] = df.added_headings.str.contains("|".join(interesting_words["usage"]), case=False)
    df = df.astype({
        "ownership_addition": bool,
        "usage_addition": bool
    })
    return df

def user_type_wrt_issues(issues, timelines_df):
    """Determine issue user status (opening, closing, both, inactive).

    Args:
        issues (pd.DataFrame): dataframe with issue data
        timelines_df (pd.DataFrame): dataframe from timeline_init

    Returns:
        pd.DataFrame: dataframe with columns "created_count", "closed_count", "user_status" for each user of each repo in each week of life of the repo
    """
    # count number of created and closed issues by user + week
    created = issues.groupby(["github_user_cleaned_url", "user", "week_since_repo_creation_created_at"])["state"].count().rename("created_count")
    created.index.rename({"week_since_repo_creation_created_at": "week_since_repo_creation"}, inplace=True)
    closed = issues.groupby(["github_user_cleaned_url", "closed_by", "week_since_repo_creation_closed_at"])["state"].count().rename("closed_count")
    closed.index.rename({"week_since_repo_creation_closed_at": "week_since_repo_creation", "closed_by": "user"}, inplace=True)
    issues_by_user = pd.merge(created, closed, left_index=True, right_index=True, how="outer").reset_index()
    issues_by_user["week_since_repo_creation"] = issues_by_user["week_since_repo_creation"].astype(int)
    issue_users_per_repo = issues_by_user.groupby("github_user_cleaned_url")["user"].unique()
    # build timeline DataFrame
    df = pd.merge(timelines_df, issue_users_per_repo, left_index=True, right_index=True, how="left").explode("user")
    df = df.reset_index().set_index(["github_user_cleaned_url", "week_since_repo_creation", "user"])
    issues_by_user = issues_by_user.set_index(["github_user_cleaned_url", "week_since_repo_creation", "user"])
    df = pd.merge(df, issues_by_user, left_index=True, right_index=True, how="left")
    df.fillna(0, inplace=True)
    # determine user status with window of 12 weeks onwards
    windowed_issue_user_df = df.groupby(level="user").rolling(window=12, min_periods=0).sum().droplevel(0)
    conditions = [(windowed_issue_user_df.created_count > 0) & (windowed_issue_user_df.closed_count == 0),
                  (windowed_issue_user_df.created_count == 0) & (windowed_issue_user_df.closed_count > 0),
                  (windowed_issue_user_df.created_count > 0) & (windowed_issue_user_df.closed_count > 0)]
    choices = ["opening", "closing", "both"]
    windowed_issue_user_df["user_status"] = np.select(conditions, choices, default="inactive")
    return windowed_issue_user_df

def user_type_wrt_commits(contributions):
    """Determine commit author status (active, inactive) and number of commits over time.

    Args:
        contributions (pd.DataFrame): dataframe with GitHub commit data

    Returns:
        pd.DataFrame: dataframe with columns 'commits', 'active_contributors' for each repo, week and user
    """
    team_df = contributions[["github_user_cleaned_url", "author", "week_since_repo_creation_week_co", "commits"]].set_index(["github_user_cleaned_url", "author", "week_since_repo_creation_week_co"]).sort_index()
    # user is active contributor if made at least one commit in last 12 weeks
    windowed_team_df = team_df.groupby(level=["github_user_cleaned_url", "author"]).rolling(window=12, min_periods=0).sum().droplevel([0, 1])
    windowed_team_df["active_contributors"] = windowed_team_df.commits > 0
    windowed_team_df.index.rename({"week_since_repo_creation_week_co": "week_since_repo_creation"}, inplace=True)
    return windowed_team_df

def no_open_and_closed_issues(issues, timelines_df):
    """Build a timeline of weekly open and closed issue counts.

    Args:
        issues (pd.DataFrame): dataframe with issue data
        timelines_df (pd.DataFrame): dataframe from timeline_init

    Returns:
        pd.DataFrame: dataframe with columns closed_count, open_count for each repo and week
    """
    timelines_df.reset_index(inplace=True)
    # merge weeks for issue opening events
    opened_issues_weekly_df = pd.merge(timelines_df, issues[["github_user_cleaned_url", "week_since_repo_creation_created_at"]], how="left", left_on=["github_user_cleaned_url", "week_since_repo_creation"], right_on=["github_user_cleaned_url", "week_since_repo_creation_created_at"])
    opened_issues_weekly_df["week_since_repo_creation"].fillna(opened_issues_weekly_df["week_since_repo_creation_created_at"], inplace=True)  # NaN will happen for issues created in negative weeks
    # merge weeks for issue closing events
    closed_issues_weekly_df = pd.merge(timelines_df, issues[["github_user_cleaned_url", "week_since_repo_creation_closed_at"]], how="left", left_on=["github_user_cleaned_url", "week_since_repo_creation"], right_on=["github_user_cleaned_url", "week_since_repo_creation_closed_at"])
    closed_issues_weekly_df["week_since_repo_creation"].fillna(closed_issues_weekly_df["week_since_repo_creation_closed_at"], inplace=True)  # NaN will happen for issues created in negative weeks
    # cumulative counts
    count_open = opened_issues_weekly_df.groupby(["github_user_cleaned_url", "week_since_repo_creation"])["week_since_repo_creation_created_at"].count().groupby(level=0).cumsum()
    count_closed = closed_issues_weekly_df.groupby(["github_user_cleaned_url", "week_since_repo_creation"])["week_since_repo_creation_closed_at"].count().groupby(level=0).cumsum().rename("closed_count")
    issue_counts_df = pd.DataFrame(count_closed)
    issue_counts_df["open_count"] = count_open - issue_counts_df["closed_count"]
    issue_counts_df = issue_counts_df.astype({
        "closed_count": int,
        "open_count": int
    })
    return issue_counts_df
       
def engagement(forks, stars, timelines_df):
    """Build a timeline of weekly forks and stars counts.

    Args:
        forks (pd.DataFrame): dataframe with fork events data
        stars (pd.DataFrame): dataframe with star events data
        timelines_df (pd.DataFrame): dataframe from timeline_init

    Returns:
        pd.DataFrame: dataframe with columns forks_count, stars_count for each repo and week
    """
    forks_df = forks[["github_user_cleaned_url", "week_since_repo_creation_date", "user"]].groupby(["github_user_cleaned_url", "week_since_repo_creation_date"]).count().rename(columns={"user": "forks_count"}).sort_index()
    stars_df = stars[["github_user_cleaned_url", "week_since_repo_creation_date", "user"]].groupby(["github_user_cleaned_url", "week_since_repo_creation_date"]).count().rename(columns={"user": "stars_count"}).sort_index()
    engagement_df = pd.merge(timelines_df, forks_df, left_on=["github_user_cleaned_url", "week_since_repo_creation"], right_index=True, how="outer")
    engagement_df = pd.merge(engagement_df, stars_df, left_on=["github_user_cleaned_url", "week_since_repo_creation"], right_index=True, how="outer").fillna(0)
    engagement_df = engagement_df.set_index(["github_user_cleaned_url", "week_since_repo_creation"])
    engagement_df = engagement_df.groupby(level=0).cumsum()
    engagement_df = engagement_df.astype({
        "forks_count": int,
        "stars_count": int
    })
    return engagement_df

def date_highlights(readme_history, contents, paper_data, timelines_df):
    """_summary_

    Args:
        readme_history (pd.DataFrame): dataframe with columns 'github_user_cleaned_url', 'week_since_repo_creation_author_date', 'ownership_addition', 'usage_addition', 'added_cites'
        contents (pd.DataFrane): dataframe with columns 'github_user_cleaned_url', 'week_since_repo_creation_citation_added', 'week_since_repo_creation_contributing_added'
        paper_data (pd.DataFrame): dataframe with columns 'github_user_cleaned_url', 'week_since_repo_creation_date'
        timelines_df (pd.DataFrame): dataframe from timeline_init

    Returns:
        pd.DataFrame: dataframe with columns paper_published, contributing_file_added, citation_file_added, citation_added, usage_added, ownership_added for each repo and week
    """
    timelines_df.set_index(["github_user_cleaned_url", "week_since_repo_creation"], inplace=True)
    event_weeks_data = {}
    event_weeks_data["ownership_added"] = readme_history[readme_history.ownership_addition].loc[:, ["week_since_repo_creation_author_date", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_author_date": "week_since_repo_creation"})
    event_weeks_data["usage_added"] = readme_history[readme_history.usage_addition].loc[:, ["week_since_repo_creation_author_date", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_author_date": "week_since_repo_creation"})
    event_weeks_data["citation_added"] = readme_history[(readme_history.added_cites != "[]") & (readme_history.added_cites.notna())].loc[:, ["week_since_repo_creation_author_date", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_author_date": "week_since_repo_creation"})
    event_weeks_data["citation_file_added"] = contents[contents.week_since_repo_creation_citation_added.notna()].loc[:, ["week_since_repo_creation_citation_added", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_citation_added": "week_since_repo_creation"})
    event_weeks_data["contributing_file_added"] = contents[contents.week_since_repo_creation_contributing_added.notna()].loc[:, ["week_since_repo_creation_contributing_added", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_contributing_added": "week_since_repo_creation"})
    event_weeks_data["paper_published"] = paper_data[paper_data.week_since_repo_creation_date.notna()].loc[:, ["week_since_repo_creation_date", "github_user_cleaned_url"]].rename(columns={"week_since_repo_creation_date": "week_since_repo_creation"})
    for k, v in event_weeks_data.items():
        v[k] = True
        v.set_index(["github_user_cleaned_url", "week_since_repo_creation"], inplace=True)
        timelines_df = pd.merge(timelines_df, v, how="left", left_index=True, right_index=True)
        timelines_df = timelines_df.fillna(value={k: False})
    return timelines_df

def timelines_init(metadata, contents, contributions, forks, stars, issues, readme_history):
    """Prepare timelines dataframe with one row for each "week of life" of each GitHub repository.

    Args:
        metadata (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        contents (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        contributions (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        forks (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        stars (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        issues (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"
        readme_history (pd.DataFrame): respective dataframe with aggregated columns "week_since_repo_creation_{original_column_name}"

    Returns:
        pd.DataFrame: dataframe with columns "github_user_cleaned_url" and "week_since_repo_creation"
    """
    def merge_min_max_weeks(min_max_week_df, df, week_col, name):
        if type(week_col) == str:
            max_series = df.groupby("github_user_cleaned_url")[week_col].max().rename(f"max_{name}")
            min_series = df.groupby("github_user_cleaned_url")[week_col].min().rename(f"min_{name}")
        elif type(week_col) == list:
            max_series = df.groupby("github_user_cleaned_url")[week_col].max().fillna(0).max(axis=1).rename(f"max_{name}")
            min_series = df.groupby("github_user_cleaned_url")[week_col].min().fillna(0).min(axis=1).rename(f"min_{name}")
        min_max_week_df = pd.merge(min_max_week_df, max_series, how="left", left_on="github_user_cleaned_url", right_index=True)
        min_max_week_df = pd.merge(min_max_week_df, min_series, how="left", left_on="github_user_cleaned_url", right_index=True)
        return min_max_week_df
    # determine max week from all dataframes
    min_max_week_df = pd.DataFrame({"github_user_cleaned_url": metadata["github_user_cleaned_url"]})
    min_max_week_df = merge_min_max_weeks(min_max_week_df, contents, ["week_since_repo_creation_citation_added", "week_since_repo_creation_contributing_added"], "week_contents")
    min_max_week_df = merge_min_max_weeks(min_max_week_df, contributions, "week_since_repo_creation_week_co", "week_contributions")
    min_max_week_df = merge_min_max_weeks(min_max_week_df, forks, "week_since_repo_creation_date", "week_forks")
    min_max_week_df = merge_min_max_weeks(min_max_week_df, stars, "week_since_repo_creation_date", "week_stars")
    min_max_week_df = merge_min_max_weeks(min_max_week_df, issues, ["week_since_repo_creation_created_at", "week_since_repo_creation_closed_at"], "week_issues")
    min_max_week_df = merge_min_max_weeks(min_max_week_df, readme_history, "week_since_repo_creation_author_date", "week_readme_history")
    min_max_week_df = min_max_week_df.fillna(0)
    # determine overall min and max week
    max_week_df = min_max_week_df.set_index("github_user_cleaned_url").max(axis=1).rename("max_week").astype(int)
    min_week_df = min_max_week_df.set_index("github_user_cleaned_url").min(axis=1).rename("min_week").astype(int)
    min_max_week_df = pd.merge(max_week_df, min_week_df, left_index=True, right_index=True).reset_index()
    # add entry for each repo life week
    #min_max_week_df["week_since_repo_creation"] = min_max_week_df["max_week"].map(lambda end: np.arange(end+1))
    min_max_week_df["week_since_repo_creation"] = min_max_week_df.apply(lambda row: np.arange(row["min_week"], row["max_week"]+1), axis=1)
    min_max_week_df.drop(["min_week", "max_week"], axis=1, inplace=True)
    timelines_df = min_max_week_df.explode("week_since_repo_creation")
    timelines_df = timelines_df.set_index("github_user_cleaned_url")
    return timelines_df

def main(githubdir, eprintsdir, outdir, verbose):
    info(verbose, f"Loading data...")
    metadata = load_data(githubdir, "metadata.csv", "created_at")
    contents = load_data(githubdir, "contents.csv", ["citation_added", "contributing_added"])
    contributions = load_data(githubdir, "contributions.csv", "week_co")
    forks = load_data(githubdir, "forks.csv", "date")
    stars = load_data(githubdir, "stars.csv", "date")
    issues = load_data(githubdir, "issues.csv", ["created_at", "closed_at"])
    readme_history = load_data(githubdir, "readme_history.csv", "author_date")
    paper_data = load_data(os.path.join(eprintsdir, "cleaned_repo_urls"), "joined.csv", "date")
    info(verbose, "Data loading complete.")

    info(verbose, "Preprocessing...")
    contents = aggregate_week_since_repo_creation(metadata, contents, ["citation_added", "contributing_added"])
    contributions = aggregate_week_since_repo_creation(metadata, contributions, "week_co")
    forks = aggregate_week_since_repo_creation(metadata, forks, "date")
    stars = aggregate_week_since_repo_creation(metadata, stars, "date")
    issues = aggregate_week_since_repo_creation(metadata, issues, ["created_at", "closed_at"])
    readme_history = aggregate_week_since_repo_creation(metadata, readme_history, "author_date")
    readme_history = clean_headings(readme_history)
    paper_data = aggregate_week_since_repo_creation(metadata, paper_data, "date")

    info(verbose, "Aggregating overall...")
    contents = license_type(contents)
    contents = readme_size_classification(contents)
    engagement_df = engagement_counts(stars, forks)
    contributors = team_size(contributions)
    max_active_contributors = contributors.reset_index().groupby("github_user_cleaned_url")["active_contributors"].max().rename("max_active_contributors")
    overall_df = pd.merge(
        pd.merge(
            pd.merge(
                metadata, contents,
                on="github_user_cleaned_url",
                how="left"
            ), engagement_df,
            on="github_user_cleaned_url",
            how="left"
        ), max_active_contributors,
        how="left",
        left_on="github_user_cleaned_url",
        right_index=True
    )
    overall_df.to_csv(os.path.join(outdir, "aggregated_overall.csv"))
    info(verbose, "Overall aggregation complete.")

    info(verbose, "Aggregating timelines...")
    readme_history = analyse_headings(readme_history)
    timelines_df = timelines_init(metadata, contents, contributions, forks, stars, issues, readme_history)
    issue_users_timeline_df = user_type_wrt_issues(issues, timelines_df)
    commit_authors_timeline_df = user_type_wrt_commits(contributions)
    issue_users_timeline_df.to_csv(os.path.join(outdir, "aggregated_issue_user_timeline.csv"))
    commit_authors_timeline_df.to_csv(os.path.join(outdir, "aggregated_commit_author_timeline.csv"))
    issue_counts_df = no_open_and_closed_issues(issues, timelines_df)
    engagement_df = engagement(forks, stars, timelines_df)
    highlights_df = date_highlights(readme_history, contents, paper_data, timelines_df)
    contributors = pd.merge(timelines_df, contributors, how="left", left_index=True, right_index=True)
    contributors.fillna(value={"active_contributors": 0, "contributors": 0}, inplace=True)
    overall_timeline_df = pd.merge(
        pd.merge(
            pd.merge(
                issue_counts_df, contributors,
                left_index=True,
                right_index=True,
                how="left"
            ), engagement_df,
            left_index=True,
            right_index=True,
            how="left"
        ), highlights_df,
        left_index=True,
        right_index=True,
        how="left"
    )
    overall_timeline_df.to_csv(os.path.join(outdir, "aggregated_timeline.csv"))
    info(verbose, "Timeline aggregation complete.")

if __name__=="__main__":
    parser = argparse.ArgumentParser(
        prog="aggregate_datasets",
        description="Aggregate crawled data into output datasets."
    )
    parser.add_argument("--githubdir", default="../../data/raw/github", type=str, help="path to GitHub data directory")
    parser.add_argument("--eprintsdir", default="../../data/raw/eprints", type=str, help="path to ePrints data directory")
    parser.add_argument("--outdir", default="../../data/derived", type=str, help="path to use for output data")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.githubdir, args.eprintsdir, args.outdir, args.verbose)
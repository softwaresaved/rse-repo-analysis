import argparse
import configparser
import pandas as pd
import numpy as np
import os
import time
import traceback
from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException
from emoji import emoji_count
from pydriller import Repository
from datetime import datetime, timezone
from time import sleep

def wrap_query(f):
    """Decorator to catch arbitrary exceptions when processing repository links.

    Args:
        f (function): function to decorate
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            msg = traceback.format_exc()
            print(f"[WARNING] Executing {f.__name__} with arguments {args} failed:\n{msg}\n")
    return wrapper

def catch_rate_limit(g):
    """Execute when running into Github's rate limit: Checks when the limit resets and pauses execution until then.

    Args:
        g (github.Github): authenticated access to Github API
    """
    reset = g.get_rate_limit().core.reset.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    delta = reset - now
    sleep(delta.seconds+5)

def safe_load_repo(g, link, func_name):
    """Attempts to load a repository, catching exceptions.

    Args:
        g (github.Github): authenticated access to Github API
        link (str): repository id ("user/repo")
        func_name (str): name of parent function calling this one, for logging purposes

    Returns:
        github.Repository: if unsuccessful, returns None.
    """
    repo = None
    try:
        repo = g.get_repo(link)
    except UnknownObjectException:
        print(f"{func_name}: Could not resolve repository for URL {link}.")
    except RateLimitExceededException:
        catch_rate_limit(g)
        repo = g.get_repo(link)  # retry
    return repo

def get_access_token():
    """Reads Github API access token from config file.

    Returns:
        str: access token
    """
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

@wrap_query
def query_issues(row: pd.Series, id_key: str, g: Github):
    """Gets all available issues in a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['state', 'created_at', 'user', 'closed_at', 'closed_by']
    """
    issues = {k: [] for k in ['state', 'created_at', 'user', 'closed_at', 'closed_by']}
    repo = safe_load_repo(g, row[id_key], "query_issues")
    if repo is None:
        return None
    for tries in range(2):
        try:
            issues_paged = repo.get_issues(state='all')
            for i in issues_paged:
                issues['state'].append(i.state)
                issues['created_at'].append(i.created_at)
                issues['user'].append(i.user.login)
                issues['closed_at'].append(i.closed_at)
                issues['closed_by'].append(i.closed_by)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
    for k, v in issues.items():
        row[k] = v
    return row

@wrap_query
def query_contributions(row: pd.Series, id_key: str, g: Github):
    """Gets contribution stats in a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['author', 'year', 'week', 'commits']
    """
    contributions = {k: [] for k in ['author', 'year', 'week', 'commits']}
    repo = safe_load_repo(g, row[id_key], "query_contributions")
    if repo is None:
        return None
    for tries in range(2):
        try:
            contribution_stats = repo.get_stats_contributors()
            if contribution_stats is not None:
                for s in contribution_stats:
                    for w in s.weeks:
                        contributions['author'].append(s.author.login)
                        contributions['year'].append(w.w.year)
                        contributions['week'].append(w.w.isocalendar().week)
                        contributions['commits'].append(w.c)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
    for k, v in contributions.items():
        row[k] = v
    return row

@wrap_query
def query_readme_history(row: pd.Series, id_key: str, *args, **kwargs):
    """Goes through commit history of README file.

    Args:
        row (pd.Series): contains column with repository ID and path to its README file
        id_key (str): name of column containing repository ID

    Returns:
        pd.Series: added columns ['author_date', 'added_headings', 'deleted_headings', 'added_cites']
    """
    repo_link = row[id_key]
    readme_path = row['readme_path']
    if pd.isna(readme_path) or not readme_path.endswith('md'):
        return None
    repo_readme = Repository('https://github.com/'+repo_link, filepath=readme_path)
    history = {k: [] for k in ['author_date', 'added_headings', 'deleted_headings', 'added_cites']}
    for commit in repo_readme.traverse_commits():
        try:
            added_headings = []
            deleted_headings = []
            added_cites = []
            # look for changes to readme file in commit
            for f in commit.modified_files:
                if f.new_path == readme_path:
                    for _, line in f.diff_parsed['added']:
                        if line.startswith('#'):
                            added_headings.append(line.lstrip('# '))
                        else:
                            for indicator in ["DOI:", "doi.", "@article", "@misc"]:
                                if indicator in line :
                                    added_cites.append(line)
                    for _, line in f.diff_parsed['deleted']:
                        if line.startswith('#'):
                            deleted_headings.append(line.lstrip('# '))
                    break
            if len(added_headings) > 0 or len(deleted_headings) > 0 or len(added_cites) > 0:
                history['author_date'].append(commit.author_date)
                history['added_headings'].append(added_headings)
                history['deleted_headings'].append(deleted_headings)
                history['added_cites'].append(added_cites)
        except ValueError:  # can be raised by git on missing commits somehow
            pass
    for k, v in history.items():
        row[k] = v
    return row

@wrap_query
def query_contents(row: pd.Series, id_key: str, g: Github):
    """Gets metadata about interesting files in a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['license', 'readme_size', 'readme_path', 'readme_emojis', 'contributing_size', 'citation_added']
    """
    contents = {k: [] for k in ['license', 'readme_size', 'readme_path', 'readme_emojis', 'contributing_size', 'citation_added']}
    repo = safe_load_repo(g, row[id_key], "query_contents")
    if repo is None:
        return None
    for tries in range(2):  # allow retry
        try:
            try:  # LICENSE
                license_file = repo.get_license()
                contents['license'].append(license_file.license.key)
            except UnknownObjectException:
                contents['license'].append(None)
            try:  # README.md
                readme = repo.get_readme()
                contents['readme_size'].append(readme.size)
                readme_content = readme.decoded_content.decode()
                contents['readme_emojis'].append(emoji_count(readme_content))
                contents['readme_path'].append(readme.path)
            except UnknownObjectException:
                contents['readme_size'].append(0)
                contents['readme_emojis'].append(0)
                contents['readme_path'].append(None)
            try:  # CONTRIBUTING
                contents['contributing_size'].append(repo.get_contents("CONTRIBUTING.md").size)
            except UnknownObjectException:
                contents['contributing_size'].append(0)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
        break  # break early if no rate limit problem
    repo_citation = Repository('https://github.com/'+row[id_key], filepath="CITATION.cff")
    commits_iterator = repo_citation.traverse_commits()
    try:
        contents['citation_added'].append(next(commits_iterator).author_date)
    except StopIteration:
        contents['citation_added'].append(None)
    for k, v in contents.items():
        row[k] = v
    return row

@wrap_query
def query_stars(row: pd.Series, id_key: str, g: Github):
    """Gets stargazers of a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['date', 'user']
    """
    stars = {k: [] for k in  ['date', 'user']}
    repo = safe_load_repo(g, row[id_key], "query_stars")
    if repo is None:
        return None
    for tries in range(2):
        try:
            stargazers = repo.get_stargazers_with_dates()
            for sg in stargazers:
                stars['date'].append(sg.starred_at)
                stars['user'].append(sg.user.login)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
    for k, v in stars.items():
        row[k] = v
    return row

@wrap_query
def query_forks(row: pd.Series, id_key: str, g: Github):
    """Gets forks a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['date', 'user']
    """
    forks = {k: [] for k in ['date', 'user']}
    repo = safe_load_repo(g, row[id_key], "query_forks")
    if repo is None:
        return None
    for tries in range(2):
        try:
            forks_list = repo.get_forks()
            for f in forks_list:
                forks['date'].append(f.created_at)
                forks['user'].append(f.owner.login)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
    for k, v in forks.items():
        row[k] = v
    return row

def collect(g, df, name, func, drop_names, path):
    """Interface for calling a query function on a dataframe of repositories.

    Args:
        g (github.Github): authenticated access to Github API
        df (pandas.DataFrame): DataFrame containing relevant columns
        name (str): name of the column containing repository ID
        func (function): pointer to query function
        drop_names (list): list of columns that should be matched against NaN (if all of them are NaN, the row is dropped) - can be empty
        path (str): path to write CSV file to
    """
    d = df.apply(func, axis=1, args=(name, g))
    cols = list(d.columns)
    cols_to_ignore = list(df.columns)
    cols_to_explode = [c for c in cols if not c in cols_to_ignore]
    d = d.dropna().explode(cols_to_explode)
    if len(drop_names) > 0:
        d.dropna(axis=0, how='all', subset=drop_names, inplace=True)
    d.to_csv(path)

def crawl_repos(df, name, target_folder, verbose):
    """For each repository, retrieve contributions, contents, readme info, stars, forks and issues. All stored as CSV.

    Args:
        df (pd.DataFrame): dataset containing GitHub repository identifiers
        name (str): name of column containing the identifiers
        target_folder (str): path to folder to store CSV data in
        verbose (bool): toggles verbose output
    """
    repo_links = df[[name]]
    g = Github(get_access_token())
    if verbose:
        print("Querying contributions...")
        start = time.time()
    collect(g, repo_links, name, query_contributions,
            ['author', 'year', 'week', 'commits'],
            os.path.join(target_folder, 'contributions.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying contents...")
        start = time.time()
    collect(g, repo_links, name, query_contents, 
            [],
            os.path.join(target_folder, 'contents.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying readme history...")
        start = time.time()
    contents_df = pd.read_csv(os.path.join(target_folder, 'contents.csv'))
    collect(g, contents_df[[name, 'readme_path']], name, query_readme_history,
            [],
            os.path.join(target_folder, 'readme_history.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying stargazers...")
        start = time.time()
    collect(g, repo_links, name, query_stars, 
            [],
            os.path.join(target_folder, 'stars.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying forks...")
        start = time.time()
    collect(g, repo_links, name, query_forks, 
        [],
        os.path.join(target_folder, 'forks.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying issues...")
        start = time.time()
    collect(g, repo_links, name, query_issues,
            ['state'],
            os.path.join(target_folder, 'issues.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")

def main(path, name, verbose):
    df = pd.read_csv(path)
    target_folder = '../data'
    crawl_repos(df, name, target_folder, verbose)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Given a dataframe with columns user_name and repo_name, gather data from the corresponding GitHub repository."
    )
    parser.add_argument("-f", "--file", required=True, type=str, help="CSV file")
    parser.add_argument("-n", "--name", required=True, type=str, help="name of column containing github ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.file, args.name, args.verbose)
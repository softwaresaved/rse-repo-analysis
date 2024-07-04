import argparse
import pandas as pd
import os
import time
from github import Github
from github.GithubException import RateLimitExceededException
from utils import wrap_query, catch_rate_limit, collect, safe_load_repo, get_access_token


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
                for inner_tries in range(2):
                    try:
                        stars['date'].append(sg.starred_at)
                        stars['user'].append(sg.user.login)
                    except RateLimitExceededException:
                        if inner_tries == 0:
                            catch_rate_limit(g)
                        else:
                            raise
                    break
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
        break
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
                for inner_tries in range(2):
                    try:
                        forks['date'].append(f.created_at)
                        forks['user'].append(f.owner.login)
                    except RateLimitExceededException:
                        if inner_tries == 0:
                            catch_rate_limit(g)
                        else:
                            raise
                    break
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
        break
    for k, v in forks.items():
        row[k] = v
    return row

def crawl_repos(df, name, target_folder, verbose):
    """For each repository, retrieve stars and forks. Stored as separate CSV.

    Args:
        df (pd.DataFrame): dataset containing GitHub repository identifiers
        name (str): name of column containing the identifiers
        target_folder (str): path to folder to store CSV data in
        verbose (bool): toggles verbose output
    """
    repo_links = df[[name]]
    repo_links = repo_links.drop_duplicates()
    g = Github(get_access_token())
    if verbose:
        print(g.rate_limiting)
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

def main(path, name, datadir, verbose):
    df = pd.read_csv(path)
    target_folder = datadir
    crawl_repos(df, name, target_folder, verbose)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Given a dataframe with a column indicating the GitHub repository ID, gather data from the corresponding GitHub repository."
    )
    parser.add_argument("-f", "--file", required=True, type=str, help="CSV file")
    parser.add_argument("-n", "--name", required=True, type=str, help="name of column containing github ID")
    parser.add_argument("--datadir", default="../../data/raw/eprints/", help="directory to write ePrints data to")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.file, args.name, args.datadir, args.verbose)
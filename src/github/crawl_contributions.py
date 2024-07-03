import argparse
import pandas as pd
import os
import time
from github import Github
from github.GithubException import RateLimitExceededException
from utils import wrap_query, catch_rate_limit, collect, safe_load_repo, get_access_token

@wrap_query
def query_contributions(row: pd.Series, id_key: str, g: Github):
    """Gets contribution stats in a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['author', 'week_co', 'commits']
    """
    contributions = {k: [] for k in ['author', 'week_co', 'commits']}
    repo = safe_load_repo(g, row[id_key], "query_contributions")
    if repo is None:
        return None
    for tries in range(2):
        try:
            contribution_stats = repo.get_stats_contributors()
            if contribution_stats is not None:
                for inner_tries in range(2):
                    try:
                        for s in contribution_stats:
                            for w in s.weeks:
                                contributions['author'].append(s.author.login)
                                contributions['week_co'].append(w.w)
                                contributions['commits'].append(w.c)
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
    for k, v in contributions.items():
        row[k] = v
    return row

def crawl_repos(df, name, target_folder, verbose):
    """For each repository, retrieve contributions, contents, readme info, stars, forks and issues. All stored as CSV.

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
        print("Querying contributions...")
        start = time.time()
    collect(g, repo_links, name, query_contributions,
            ['author', 'week_co', 'commits'],
            os.path.join(target_folder, 'contributions.csv'))
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
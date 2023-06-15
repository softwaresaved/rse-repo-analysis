import argparse
import pandas as pd
import os
import time
from github import Github
from github.GithubException import RateLimitExceededException
from utils import wrap_query, catch_rate_limit, collect, safe_load_repo, get_access_token

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
                for inner_tries in range(2):
                    try:
                        issues['state'].append(i.state)
                        issues['created_at'].append(i.created_at)
                        issues['user'].append(i.user.login)
                        issues['closed_at'].append(i.closed_at)
                        issues['closed_by'].append(i.closed_by)
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
    for k, v in issues.items():
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
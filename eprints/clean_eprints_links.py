import pandas as pd
import argparse
import re
import Levenshtein
import configparser
from github import Github, GithubException
from unidecode import unidecode

def get_access_token():
    """Read Github API access token from config file.

    Returns:
        str: Access Token
    """
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def clean_by_pattern(row, domain):
    """Parsing results often contain other text at the end of the link.
    The real link is often separated from the following text using a dot or number (from the next footnote),
    so we match against domain/username/reponame and assume that the reponame is not allowed to contain dots or number.
    This is not true, but usually works well. Early cut-offs can also be corrected in the clean_by_user function.

    Args:
        row (pd.Series): row with a column url

    Returns:
        list<str>: List of cleaned links.
    """
    pattern = rf"{domain}/[A-Za-z0-9-]+/[A-Za-z_\-]+"
    cleaned = re.findall(pattern, unidecode(row['domain_url']))
    return cleaned

def clean_by_user(row, column, verbose):
    """Clean links by looking up user-repo mapping via Github API.

    Args:
        row (pd.Series): row to process
        column (str): column name
        verbose (bool): whether to produce additional output

    Returns:
        str: repository identifier (ie. 'user/repo'), may be empty
    """
    g = Github(get_access_token())
    _, username, repo_name = unidecode(row[column]).split("/")
    try:
        repo_id = f"{username}/{repo_name}"
        r = g.get_repo(repo_id)
    except GithubException:
        try:
            user = g.get_user(username)
        except GithubException:  # user not found
            return None
        bestmatch = ""
        maxratio = 0.
        for r in user.get_repos():
            ratio = Levenshtein.ratio(r.name, repo_name)
            if ratio > 0.7 and ratio > maxratio:
                bestmatch = r.name
                maxratio = ratio
        if bestmatch != "":
            repo_id = f"{username}/{bestmatch}"
            if verbose:
                print(f"Matched user {username}'s repo {bestmatch} with extracted link {row[column]}.")
        else:  # no match found
            repo_id = None
    return repo_id

def main(repo, date, domain, verbose):
    df = pd.read_csv(f"../data/extracted_urls_{repo}_{date}_{domain}.csv")
    df["pattern_cleaned_url"] = df.apply(clean_by_pattern, args=(domain,), axis=1)
    df = df.explode("pattern_cleaned_url", ignore_index=True)  # expand DataFrame for when multiple links are found
    df.drop_duplicates(subset=['title', 'author_for_reference', 'pattern_cleaned_url'], inplace=True)
    df.dropna(axis=0, subset=['pattern_cleaned_url'], inplace=True)
    if domain == "github.com":
        df["github_user_cleaned_url"] = df.apply(clean_by_user, args=("pattern_cleaned_url", verbose), axis=1)
        #df.drop_duplicates(subset=['title', 'author_for_reference', 'github_user_cleaned_url'], inplace=True)
        df.dropna(axis=0, subset=['github_user_cleaned_url'], inplace=True)
    df.to_csv(f"../data/cleaned_urls_{repo}_{date}_{domain}.csv", index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="clean_eprints_links",
        description="Clean the repository links retrieved from ePrints. Only works for Github Links for now."
    )
    parser.add_argument("--repo", required=True, type=str, help="name of ePrints repository (i.e. domain)")
    parser.add_argument("--date", required=True, type=str, help="date range for filtering ePrints, e.g. 2021-2022")
    parser.add_argument("--domain", required=True, type=str, help="domain to match against (only one can be provided for now, e.g. github.com)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.repo, args.date, args.domain, args.verbose)

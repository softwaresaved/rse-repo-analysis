import json
import argparse
import re
import requests
from github import Github, GithubException
import Levenshtein
import difflib
import configparser

def get_access_token():
    """Read Github API access token from config file.

    Returns:
        str: Access Token
    """
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def clean_by_pattern(parsed_links, domain):
    """Parsing results often contain other text at the end of the link.
    The real link is often separated from the following text using a dot or number (from the next footnote),
    so we match against domain/username/reponame and assume that the reponame is not allowed to contain dots or number.
    This is not true, but usually works well. Early cut-offs can also be corrected in the clean_by_user function.

    Args:
        parsed_links (dict<str: list<str>>): Dictionary of paper download link and extracted links.

    Returns:
        dict<str: list<str>>: Dictionary of paper download link and cleaned links.
    """
    cleaned_links = {}
    pattern = rf"{domain}/[A-Za-z0-9-]+/[A-Za-z_\-]+"
    for key, val in parsed_links.items():
        if len(val) > 0:
            cleaned_links[key] = []
            for link in val:
                cleaned_links[key] += re.findall(pattern, link)
    return cleaned_links

def clean_by_user(pattern_cleaned_links, verbose):
    """Clean links by looking up user-repo mapping via Github API.

    Args:
        pattern_cleaned_links (dict<str: list<str>>): Dictionary of paper download link and cleaned links.
        verbose (bool): whether to produce additional output

    Returns:
        dict<str: list<dict<str: str>>>: Dictionary mapping paper download link to list of dictionaries holding username and repo name.
    """
    g = Github(get_access_token())
    cleaned_links = {}
    for paper, link_list in pattern_cleaned_links.items():
        cleaned_links[paper] = []
        for l in link_list:
            _, username, repo_name = l.split("/")
            try:
                r = g.get_repo(f"{username}/{repo_name}")
                cleaned_links[paper].append({"user": username, "repo": repo_name})
            except GithubException:
                user = g.get_user(username)
                bestmatch = ""
                maxratio = 0.
                for r in user.get_repos():
                    ratio = Levenshtein.ratio(r.name, repo_name)
                    if ratio > 0.7 and ratio > maxratio:
                        bestmatch = r.name
                        maxratio = ratio
                if bestmatch != "":
                    cleaned_links[paper].append({"user": username, "repo": bestmatch})
                    if verbose:
                        print(f"Matched user {username}'s repo {bestmatch} with extracted link {l}.")
    return cleaned_links

def main(repo, date, domain, verbose):
    with open(f"data/extracted_urls_{repo}_{date}_{domain}.json", "r") as f:
        parsed_links = json.load(f)
    pattern_cleaned_links = clean_by_pattern(parsed_links, domain)
    if domain == "github.com":
        cleaned_links = clean_by_user(pattern_cleaned_links, verbose)
        with open(f"data/cleaned_urls_{repo}_{date}_{domain}.json", "w") as f:
            json.dump(cleaned_links, f, indent=4)
    else:
        print("Cannot clean by user for other domains than github.com, sorry!")
        with open(f"data/cleaned_urls_{repo}_{date}_{domain}.json", "w") as f:
            json.dump(pattern_cleaned_links, f)

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
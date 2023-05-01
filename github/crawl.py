import argparse
import configparser
import pandas as pd
import numpy as np
import os
import time
from github import Github
from emoji import emoji_count
from pydriller import Repository
from itertools import chain

def get_access_token():
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def query_issues(repo_link: str, g: Github):
    issues = []
    try:
        repo = g.get_repo(repo_link)
    except:
        print(f"query_issues: Could not resolve repository for URL {repo_link}.")
        return np.array([[repo_link, None, None, None, None, None]])
    issues_paged = repo.get_issues(state='all')
    if issues_paged.totalCount == 0:
        issues.append([repo_link, None, None, None, None, None])
    for i in issues_paged:
        issues.append([repo_link, i.state, i.created_at, i.user.login, i.closed_at, i.closed_by])
    issues = np.array(issues)
    return issues

def query_contributions(repo_link: str, g: Github):
    contributions = []
    try:
        repo = g.get_repo(repo_link)
    except:
        print(f"query_contributions: Could not resolve repository for URL {repo_link}.")
        return np.array([[repo_link, None, None, None, None]])
    contribution_stats = repo.get_stats_contributors()
    if contribution_stats is not None:
        for s in contribution_stats:
            for w in s.weeks:
                contributions.append([repo_link, s.author.login, w.w.year, w.w.isocalendar().week, w.c])
    else:
        contributions.append([repo_link, None, None, None, None])
    contributions = np.array(contributions)
    return contributions

def query_readme_history(row):
    repo_link = row['repo_link']
    readme_path = row['readme_path']
    if not readme_path.endswith('md'):
        return None
    repo_readme = Repository('https://github.com/'+repo_link, filepath=readme_path)
    history = []
    for commit in repo_readme.traverse_commits():
        try:
            for f in commit.modified_files:
                if f.new_path == readme_path:
                    added_headings = []
                    deleted_headings = []
                    added_cites = []
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
            if len(added_headings) > 0 or len(deleted_headings) > 0 or len(added_cites) > 0:
                history.append([repo_link, commit.author_date, added_headings, deleted_headings, added_cites])
        except ValueError:  # can be raised by git on missing commits somehow
            pass
    return history

def query_contents(repo_link: str, g: Github):
    contents = []
    try:
        repo = g.get_repo(repo_link)
    except:
        print(f"query_contents: Could not resolve repository for URL {repo_link}.")
        return np.array([[repo_link, None, 0, None, 0, 0]])
    try:  # LICENSE
        license_file = repo.get_license()
        license_entry = license_file.license.key
    except:
        license_entry = None
    try:  # README.md
        readme = repo.get_readme()
        readme_size = readme.size
        readme_content = readme.decoded_content.decode()
        readme_emojis = emoji_count(readme_content)
        readme_path = readme.path
    except:
        readme_size = 0
        readme_emojis = 0
        readme_path = None
    try:  # CONTRIBUTING
        contrib_file_size = repo.get_contents("CONTRIBUTING.md").size
    except:
        contrib_file_size = 0
    contents.append([repo_link, license_entry, readme_size, readme_path, readme_emojis, contrib_file_size])
    contents = np.array(contents)
    return contents

def collect(series, func, column_names, drop_names, path):
    g = Github(get_access_token())
    data = series.apply(func, args=(g,))
    data_arr = np.concatenate(data.tolist())
    df = pd.DataFrame(data_arr, columns=column_names)
    if len(drop_names) > 0:
        df.dropna(axis=0, how='all', subset=drop_names, inplace=True)
    df.to_csv(path)

def crawl_repos(df, name, target_folder, verbose):
    """For each repository, retrieve contributions, contents.

    Args:
        df (pd.DataFrame): dataset containing GitHub repository identifiers
        name (str): name of column containing the identifiers
        target_folder (str): path to folder to store CSV data in
        verbose (bool): toggles verbose output

    Returns:
        (pd.DataFrame, pd.DataFrame): one data frame holding info on contributions, one data frame holding info on licenses.
            - contributions dataframe columns:
                - repo_link: GitHub ID from original data frame
                - author: contributor to repository
                - year, week: determine the week of contributions in question
                - commits: number of commits in that specific week
            - contents dataframe columns:
                - repo_link: GitHub ID from original data frame
                - license: license key if license was found (e.g. mit, lgpl-3.0, mpl-2.0, ... (https://docs.github.com/en/rest/licenses?apiVersion=2022-11-28#get-all-commonly-used-licenses))
                - readme_size: size of README file, 0 if none was found
                - readme_headings: headings found in README files
                - readme_emojis: number of emojis found in README file
                - contributing_size: size of CONTRIBUTING.md file, 0 if none was found
    """
    repo_links = df[name]
    if verbose:
        print("Querying contributions...")
        start = time.time()
    collect(repo_links, query_contributions,
            ['repo_link', 'author', 'year', 'week', 'commits'],
            ['author', 'year', 'week', 'commits'],
            os.path.join(target_folder, 'contributions.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying contents...")
        start = time.time()
    collect(repo_links, query_contents, 
            ['repo_link', 'license', 'readme_size', 'readme_path', 'readme_emojis', 'contributing_size'],
            [],
            os.path.join(target_folder, 'contents.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying readme history...")
        start = time.time()
    contents_df = pd.read_csv(os.path.join(target_folder, 'contents.csv'))
    rm_history = contents_df[['repo_link', 'readme_path']].apply(query_readme_history, axis=1)
    rm_history_concatenated = list(chain.from_iterable(rm_history.tolist()))
    rm_history_df = pd.DataFrame(rm_history_concatenated, columns=['repo_link', 'author_date', 'added_headings', 'deleted_headings', 'added_cites'])
    rm_history_df.to_csv(os.path.join(target_folder, 'readme_history.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying issues...")
        start = time.time()
    collect(repo_links, query_issues,
            ['repo_link', 'state', 'created_at', 'user', 'closed_at', 'closed_by'],
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
import argparse
import configparser
import re
import pandas as pd
import numpy as np
from github import Github
from pyspark.sql import SparkSession  # couldn't get this to work, throws AssertionError when pandas_udf are useda
from tqdm import tqdm
from emoji import emoji_count

def get_access_token():
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def query_contributions(repo_link: str, g: Github):
    contributions = []
    try:
        repo = g.get_repo(repo_link)
    except:
        print(f"Could not resolve repository for URL {repo_link}.")
        return None
    contribution_stats = repo.get_stats_contributors()
    if contribution_stats is not None:
        for s in contribution_stats:
            for w in s.weeks:
                contributions.append([repo_link, s.author.login, w.w.year, w.w.isocalendar().week, w.c])
    else:
        contributions.append([repo_link, None, None, None, None])
    contributions = np.array(contributions)
    return contributions

def query_contents(repo_link: str, g: Github):
    contents = []
    try:
        repo = g.get_repo(repo_link)
    except:
        print(f"Could not resolve repository for URL {repo_link}.")
        return None
    try:
        license_file = repo.get_license()
        license_entry = license_file.license.key
    except:
        license_entry = None
    try:
        readme = repo.get_readme()
        readme_entry = readme.size
        readme_content = readme.decoded_content.decode()
        pattern = r"#+ .*\n"
        headings = re.findall(pattern, readme_content)
        cleaned_headings = []
        for h in headings:
            cleaned_headings.append(h.strip("# \n"))
        readme_emojis = emoji_count(readme_content)
    except:
        readme_entry = 0
        cleaned_headings = [None]
        readme_emojis = 0
    for h in cleaned_headings:
        contents.append([repo_link, license_entry, readme_entry, h, readme_emojis])
    contents = np.array(contents)
    return contents

def crawl_repos(df, name):
    """For each repository, retrieve contributions, contents.

    Args:
        df (pd.DataFrame): dataset containing GitHub repository identifiers
        name (str): name of column containing the identifiers

    Returns:
        (pd.DataFrame, pd.DataFrame): one data frame holding info on contributions, one data frame holding info on licenses.
            - contributions dataframe columns:
                - repo_link: GitHub ID from original data frame
                - author: contributor to repository
                - year, week: determine the week of contributions in question
                - commits: number of commits in that specific week
            - license dataframe columns:
                - repo_link: GitHub ID from original data frame
                - license: license key if license was found (e.g. mit, lgpl-3.0, mpl-2.0, ... (https://docs.github.com/en/rest/licenses?apiVersion=2022-11-28#get-all-commonly-used-licenses))
                - readme_size: size of README file, 0 if none was found
                - readme_headings: headings found in README files
                - readme_emojis: number of emojis found in README file
    """
    repo_links = df[name]
    contributions = repo_links.apply(query_contributions, args=(Github(get_access_token()),))
    contents = repo_links.apply(query_contents, args=(Github(get_access_token()),))
    contributions = np.concatenate(contributions.tolist())
    contents = np.concatenate(contents.tolist())
    contributions_df = pd.DataFrame(contributions, columns=['repo_link', 'author', 'year', 'week', 'commits'])
    contents_df = pd.DataFrame(contents, columns=['repo_link', 'license', 'readme_size', 'readme_headings', 'readme_emojis'])
    return contributions_df, contents_df

def main(path, name, verbose):
    #spark = SparkSession.builder.getOrCreate()
    #df = spark.read.csv(path, header=True)
    df = pd.read_csv(path)
    #df = df.withColumn("output", graze_repo("user_name", "repo_name"))
    #df.select(combine("user_name", "repo_name")).show()
    contributions_df, contents_df = crawl_repos(df, name)
    contributions_df.to_csv(f'data/contributions.csv')
    contents_df.to_csv(f'data/contents.csv')

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
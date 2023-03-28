import argparse
import configparser
import pandas as pd
import numpy as np
from github import Github
from pyspark.sql import SparkSession  # couldn't get this to work, throws AssertionError when pandas_udf are useda
from tqdm import tqdm

def get_access_token():
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def compose_repo_link(row: np.array) -> str:
    link = f"{row[0]}/{row[1]}"
    return link

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
    except:
        readme_entry = 0
    contents.append([repo_link, license_entry, readme_entry])
    contents = np.array(contents)
    return contents

def crawl_repos(df):
    """For each repository, retrieve contributions, contents.

    Args:
        df (pd.DataFrame): dataset with Github username and repo name

    Returns:
        (pd.DataFrame, pd.DataFrame): one data frame holding info on contributions, one data frame holding info on licenses.
            - contributions dataframe columns:
                - repo_link: combination of user_name/repo_name from original data frame
                - author: contributor to repository
                - year, week: determine the week of contributions in question
                - commits: number of commits in that specific week
            - license dataframe columns:
                - repo_link: combination of user_name/repo_name from original data frame
                - license: license key if license was found (e.g. mit, lgpl-3.0, mpl-2.0, ... (https://docs.github.com/en/rest/licenses?apiVersion=2022-11-28#get-all-commonly-used-licenses))
                - readme_size: size of README file, 0 if none was found
    """
    repo_links = df.apply(compose_repo_link, axis=1, raw=True)  # CAUTION: assumes that column 0 is user, column 1 is repo
    contributions = repo_links.apply(query_contributions, args=(Github(get_access_token()),))
    contents = repo_links.apply(query_contents, args=(Github(get_access_token()),))
    contributions = np.concatenate(contributions.tolist())
    contents = np.concatenate(contents.tolist())
    contributions_df = pd.DataFrame(contributions, columns=['repo_link', 'author', 'year', 'week', 'commits'])
    contents_df = pd.DataFrame(contents, columns=['repo_link', 'license', 'readme_size'])
    return contributions_df, contents_df

def main(path, verbose):
    #spark = SparkSession.builder.getOrCreate()
    #df = spark.read.csv(path, header=True)
    df = pd.read_csv(path)
    #df = df.withColumn("output", graze_repo("user_name", "repo_name"))
    #df.select(combine("user_name", "repo_name")).show()
    contributions_df, contents_df = crawl_repos(df)
    contributions_df.to_csv(f'data/contributions.csv')
    contents_df.to_csv(f'data/contents.csv')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Given a dataframe with columns user_name and repo_name, gather data from the corresponding GitHub repository."
    )
    parser.add_argument("-f", "--file", required=True, type=str, help="CSV file")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.file, args.verbose)
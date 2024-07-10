import os
import pandas as pd
import argparse

def load_cleaned_links(repo, date, domain, datadir):
    """Read in the respective CSV file if it exists.

    Args:
        repo (str): ePrints repository name
        date (str): date range that ePrints search was filtered on
        domain (str): Git repository domain
        datadir (str): directory with ePrints data

    Returns:
        pd.DataFrame: ePrints mining results from the identified CSV
    """
    path = os.path.join(datadir, f"cleaned_repo_urls/cleaned_urls_{repo}_{date}_{domain}.csv")
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None
    return df

def main(date, domain, datadir):
    # construct list of ePrints repositories
    f = open(os.path.join(datadir, "eprints_repos.txt"), "r")
    repos = []
    for line in f.readlines():
        repos.append(line.rstrip("\n"))
    repos = sorted(repos)
    # merge cleaned data mined from all ePrints repositories
    df = None
    for repo in repos:
        repo_df = load_cleaned_links(repo, date, domain, datadir)
        if repo_df is not None:
            repo_df["repo"] = repo
            if df is None:
                df = repo_df
            else:
                df = pd.concat([df, repo_df])
    # select only URLs found on the first two pages of a repository
    filtered = df.loc[df.page_no <= 1]
    filtered.to_csv(os.path.join(datadir, f"cleaned_repo_urls/filtered_urls_{date}_{domain}.csv"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="merge_and_filter",
        description="Load cleaned links from multiple ePrints repositories, merge them into one file and filter for the links found on the first two pages."
    )
    parser.add_argument("--date", required=True, type=str, help="date range for filtering ePrints, e.g. 2021-2022")
    parser.add_argument("--domain", required=True, type=str, help="domain to match against (only one can be provided for now, e.g. github.com)")
    parser.add_argument("--datadir", default="../../data/raw/eprints/", help="directory to write ePrints data to")
    args = parser.parse_args()
    main(args.date, args.domain, args.datadir)
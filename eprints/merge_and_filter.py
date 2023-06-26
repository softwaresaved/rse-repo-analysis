import pandas as pd
import argparse

def load_cleaned_links(repo, date, domain):
    path = f"../data/cleaned_urls_{repo}_{date}_{domain}.csv"
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None
    return df

def main(date, domain):
    f = open("../data/eprints_repos.txt", "r")
    repos = []
    for line in f.readlines():
        repos.append(line.rstrip("\n"))
    repos = sorted(repos)
    df = None
    for repo in repos:
        repo_df = load_cleaned_links(repo, "2010-", "github.com")
        if repo_df is not None:
            repo_df["repo"] = repo
            if df is None:
                df = repo_df
            else:
                df = pd.concat([df, repo_df])
    filtered = df.loc[df.page_no <= 1]
    filtered.to_csv(f"../data/filtered_urls_{date}_{domain}.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="clean_eprints_links",
        description="Clean the repository links retrieved from ePrints. Only works for Github Links for now."
    )
    parser.add_argument("--date", required=True, type=str, help="date range for filtering ePrints, e.g. 2021-2022")
    parser.add_argument("--domain", required=True, type=str, help="domain to match against (only one can be provided for now, e.g. github.com)")
    args = parser.parse_args()
    main(args.date, args.domain)
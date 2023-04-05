from github import Github, GithubException
import json
import pandas as pd
import configparser
from tqdm import tqdm

def get_access_token():
    """Read Github API access token from config file.

    Returns:
        str: Access Token
    """
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def parse_samples(slice):
    samples_dict = {"user_name": [], "repo_name": [], "stars": [], "watchers": [], "forks": [], "commits_no": [], "contributors_no": [], "size_kb": []}
    for s in slice:
        samples_dict["user_name"].append(s.owner.login)
        samples_dict["repo_name"].append(s.name)
        samples_dict["stars"].append(s.get_stargazers().totalCount)
        samples_dict["watchers"].append(s.get_subscribers().totalCount)
        samples_dict["forks"].append(s.get_forks().totalCount)
        try:
            samples_dict["commits_no"].append(s.get_commits().totalCount)
        except GithubException:
            samples_dict["commits_no"].append(0)
        samples_dict["contributors_no"].append(s.get_contributors().totalCount)
        samples_dict["size_kb"].append(s.size)
    samples_df = pd.DataFrame(samples_dict)
    return samples_df

def compose_repo_link(row) -> str:
    link = f"{row['user_name']}/{row['repo_name']}"
    return link

if __name__ == "__main__":
    g = Github(get_access_token())
    samples = {}
    stars_intervals = ["<1", "1..100", "100..1000", "1000..10000", ">10000"]
    for interval in tqdm(stars_intervals):
        result = g.search_repositories(f"stars:{interval} fork:false created:>2018-01-01")
        samples[interval] = parse_samples(result[:20])
    df = pd.concat(samples.values())
    df["github_id"] = df.apply(compose_repo_link, axis=1)
    df.to_csv("../data/representative_set.csv", index=False)

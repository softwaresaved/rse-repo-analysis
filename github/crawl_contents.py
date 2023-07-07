import argparse
import pandas as pd
import os
import time
import resource
from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException
from emoji import emoji_count
from pydriller import Repository
from utils import wrap_query, catch_rate_limit, collect, safe_load_repo, get_access_token

@wrap_query
def query_readme_history(row: pd.Series, id_key: str, *args, **kwargs):
    """Goes through commit history of README file.

    Args:
        row (pd.Series): contains column with repository ID and path to its README file
        id_key (str): name of column containing repository ID

    Returns:
        pd.Series: added columns ['author_date', 'added_headings', 'deleted_headings', 'added_cites']
    """
    repo_link = row[id_key]
    readme_path = row['readme_path']
    if pd.isna(readme_path) or not readme_path.endswith('md'):
        return None
    repo_readme = Repository('https://github.com/'+repo_link, filepath=readme_path)
    history = {k: [] for k in ['author_date', 'added_headings', 'deleted_headings', 'added_cites']}
    for commit in repo_readme.traverse_commits():
        try:
            added_headings = []
            deleted_headings = []
            added_cites = []
            # look for changes to readme file in commit
            for f in commit.modified_files:
                if f.new_path == readme_path:
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
                    break
            if len(added_headings) > 0 or len(deleted_headings) > 0 or len(added_cites) > 0:
                history['author_date'].append(commit.author_date)
                history['added_headings'].append(added_headings)
                history['deleted_headings'].append(deleted_headings)
                history['added_cites'].append(added_cites)
        except ValueError:  # can be raised by git on missing commits somehow
            pass
    for k, v in history.items():
        row[k] = v
    return row

@wrap_query
def query_contents(row: pd.Series, id_key: str, g: Github):
    """Gets metadata about interesting files in a repository.

    Args:
        row (pd.Series): contains column with repository ID
        id_key (str): name of column containing repository ID
        g (Github): authenticated access to Github API

    Returns:
        pd.Series: added columns ['license', 'readme_size', 'readme_path', 'readme_emojis', 'contributing_size', 'citation_added', 'contributing_added']
    """
    contents = {k: [] for k in ['license', 'readme_size', 'readme_path', 'readme_emojis', 'contributing_size', 'citation_added', 'contributing_added']}
    repo = safe_load_repo(g, row[id_key], "query_contents")
    if repo is None:
        return None
    for tries in range(2):  # allow retry
        try:
            try:  # LICENSE
                license_file = repo.get_license()
                contents['license'].append(license_file.license.key)
            except UnknownObjectException:
                contents['license'].append(None)
            try:  # README.md
                readme = repo.get_readme()
                contents['readme_size'].append(readme.size)
                readme_content = readme.decoded_content.decode()
                contents['readme_emojis'].append(emoji_count(readme_content))
                contents['readme_path'].append(readme.path)
            except UnknownObjectException:
                contents['readme_size'].append(0)
                contents['readme_emojis'].append(0)
                contents['readme_path'].append(None)
            try:  # CONTRIBUTING
                contents['contributing_size'].append(repo.get_contents("CONTRIBUTING.md").size)
            except UnknownObjectException:
                contents['contributing_size'].append(0)
        except RateLimitExceededException:
            if tries == 0:
                catch_rate_limit(g)
            else:
                raise
        break  # break early if no rate limit problem
    repo_citation = Repository('https://github.com/'+row[id_key], filepath="CITATION.cff")
    commits_iterator = repo_citation.traverse_commits()
    try:
        contents['citation_added'].append(next(commits_iterator).author_date)
    except StopIteration:
        contents['citation_added'].append(None)
    repo_contrib_guidelines = Repository('https://github.com/'+row[id_key], filepath="CONTRIBUTING.md")
    contrib_guidelines_iterator = repo_contrib_guidelines.traverse_commits()
    try:
        contents['contributing_added'].append(next(contrib_guidelines_iterator).author_date)
    except StopIteration:
        contents['contributing_added'].append(None)
    for k, v in contents.items():
        row[k] = v
    return row

def crawl_repos(df, name, target_folder, verbose):
    """For each repository, retrieve contributions, contents, readme info, stars,

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
        print("Querying contents...")
        start = time.time()
    collect(g, repo_links, name, query_contents,
            [],
            os.path.join(target_folder, 'contents.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")
        print("Querying readme history...")
        start = time.time()
    contents_df = pd.read_csv(os.path.join(target_folder, 'contents.csv'))
    collect(g, contents_df[[name, 'readme_path']], name, query_readme_history,
            [],
            os.path.join(target_folder, 'readme_history.csv'))
    if verbose:
        end = time.time()
        print(f"Done - {end-start:.2f} seconds.")

def main(path, name, verbose):
    df = pd.read_csv(path)
    target_folder = '../data'
    crawl_repos(df, name, target_folder, verbose)

if __name__ == "__main__":
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (2000000000, hard))
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Given a dataframe with columns user_name and repo_name, gather data from the corresponding GitHub repository."
    )
    parser.add_argument("-f", "--file", required=True, type=str, help="CSV file")
    parser.add_argument("-n", "--name", required=True, type=str, help="name of column containing github ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.file, args.name, args.verbose)

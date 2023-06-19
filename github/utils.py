import configparser
import traceback
from github.GithubException import RateLimitExceededException, UnknownObjectException
from datetime import datetime, timezone
from time import sleep

def wrap_query(f):
    """Decorator to catch arbitrary exceptions when processing repository links.

    Args:
        f (function): function to decorate
    """
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            msg = traceback.format_exc()
            print(f"[WARNING] Executing {f.__name__} with arguments {args} failed:\n{msg}\n")
    return wrapper

def catch_rate_limit(g):
    """Execute when running into Github's rate limit: Checks when the limit resets and pauses execution until then.

    Args:
        g (github.Github): authenticated access to Github API
    """
    print("Catching rate limit...")
    print(g.rate_limiting)
    print("Reset: ", g.get_rate_limit().core.reset)
    reset = g.get_rate_limit().core.reset.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    delta = reset - now
    print("Now: ", now)
    print("Wait for: ", delta.seconds+60)
    sleep(delta.seconds+60)
    print("Now: ", datetime.now(tz=timezone.utc))
    print("Resume execution:",  g.get_rate_limit().core)

def safe_load_repo(g, link, func_name):
    """Attempts to load a repository, catching exceptions.

    Args:
        g (github.Github): authenticated access to Github API
        link (str): repository id ("user/repo")
        func_name (str): name of parent function calling this one, for logging purposes

    Returns:
        github.Repository: if unsuccessful, returns None.
    """
    repo = None
    try:
        repo = g.get_repo(link)
    except UnknownObjectException:
        print(f"{func_name}: Could not resolve repository for URL {link}.")
    except RateLimitExceededException:
        catch_rate_limit(g)
        repo = g.get_repo(link)  # retry
    return repo

def get_access_token():
    """Reads Github API access token from config file.

    Returns:
        str: access token
    """
    config = configparser.ConfigParser()
    config.read('../config.cfg')
    return config['ACCESS']['token']

def collect(g, df, name, func, drop_names, path):
    """Interface for calling a query function on a dataframe of repositories.

    Args:
        g (github.Github): authenticated access to Github API
        df (pandas.DataFrame): DataFrame containing relevant columns
        name (str): name of the column containing repository ID
        func (function): pointer to query function
        drop_names (list): list of columns that should be matched against NaN (if all of them are NaN, the row is dropped) - can be empty
        path (str): path to write CSV file to
    """
    d = df.apply(func, axis=1, args=(name, g))
    cols = list(d.columns)
    cols_to_ignore = list(df.columns)
    cols_to_explode = [c for c in cols if not c in cols_to_ignore]
    d = d.dropna()
    try:
        d = d.explode(cols_to_explode)
    except ValueError:
        msg = traceback.format_exc()
        print(f"[WARNING] Could not explode DataFrame:\n{msg}\n")
    if len(drop_names) > 0:
        d.dropna(axis=0, how='all', subset=drop_names, inplace=True)
    d.to_csv(path)
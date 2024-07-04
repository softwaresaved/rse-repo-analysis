# Mining GitHub repositories

All scripts in this directory expect an argument `-f` pointing to a CSV file containing a column of GitHub repository IDs, i.e. `user_name/repo_name`, and an argument `-n` indicating the name of that column.
Run the scripts with `--help` for more detail.
Additionally, all scripts use utilities provided in [`utils.py`](./utils.py), e.g. to instantiate the GitHub object and catch rate limit errors.

Each script produces one or more CSV files with data mined for all repositories.
They will thus run for a long time, and likely run into API rate limits, too.
These are caught by the scripts which then wait until the rate limit has reset (hourly).
You should use a valid GitHub API token as described in the root README.
You will only be able to reach repositories readable with your token, which will include any public repository and any repositories your user account at GitHub has access to.

Information on the collected data and resulting schemas is listed in the wiki associated with this repository.
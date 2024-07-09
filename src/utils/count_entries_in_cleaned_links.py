import argparse
import pandas as pd

def main(path):
    df = pd.read_csv(path)
    for e_r in sorted(df.eprints_repo.unique()):
        print("Repo:", e_r)
        df_temp = df[df.eprints_repo == e_r]
        print("Links:", len(df_temp.domain_url.notna()))
        print("Pattern cleaned links:", len(df_temp.pattern_cleaned_url.notna()))
        print("User cleaned links:", len(df_temp.github_user_cleaned_url.notna()))
        print("Unique links:", len(df_temp.github_user_cleaned_url.unique()))
        print("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="count_entries_in_cleaned_links",
        description="For each ePrints repository, report the number of non-null entries in the relevant columns."
    )
    parser.add_argument("-f", "--file", type=str,
                        help="CSV file containing data from all ePrints repositories",
                        default="../../data/raw/eprints/cleaned_repo_urls/joined.csv")
    args = parser.parse_args()
    main(args.file)

import pandas as pd
import argparse

def main(filepath, true_list_path, false_list_path):
    df = pd.read_csv(filepath)
    df = df[df.page_no < 2]
    created_map = {"github_repo_id": [], "mention_created": []}
    for path, v in [(true_list_path, True), (false_list_path, False)]:
        with open(path, "r") as f:
            for line in f.readlines():
                created_map["github_repo_id"].append(line.rstrip("\n"))
                created_map["mention_created"].append(v)
    created_df = pd.DataFrame(created_map)
    merged_df = created_df.merge(df, how="left", left_on="github_repo_id", right_on="github_user_cleaned_url")
    print(f"[INFO] Candidates: {len(df)}\n       Mapped: {len(created_df)}\n       Result: {len(merged_df)}")
    merged_df["date"] = pd.to_datetime(merged_df["date"])
    merged_df = merged_df.astype({
        "github_repo_id": str,
        "mention_created": bool,
        "title": str,
        "author_for_reference": str,
        "pdf_url": str,
        "page_no": int,
        "domain_url": str,
        "pattern_cleaned_url": str,
        "github_user_cleaned_url": str,
        "year": int,
        "eprints_repo": str
        })
    # correct duplicates manually
    corrected_cnt = 0
    idx = merged_df[(merged_df.github_repo_id == "IraKorshunova/folk-rnn") & (merged_df.pdf_url == "https://eprints.kingston.ac.uk/id/eprint/44298/1/Ben-Tal-O-44298-VoR.pdf")].index[0]
    merged_df.loc[idx, "mention_created"] = False
    corrected_cnt += 1
    print(f"[INFO] Manual corrections: {corrected_cnt}")
    # rename columns for clarity
    merged_df.rename(columns={
        "title": "pub_title",
        "author_for_reference": "pub_author_for_reference",
        "domain_url": "detected_github_url",
        "pattern_cleaned_url": "pattern_matched_github_url",
        "date": "eprints_date",
        "year": "eprints_pub_year",
    }, inplace=True)
    merged_df.drop(columns=["github_user_cleaned_url"], inplace=True)
    print("Schema:")
    merged_df.info()
    merged_df.to_csv("../data/outputs/eprints_w_intent.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="repo_intent",
        description="Load cleaned links from multiple ePrints repositories and merge them into one file."
    )
    parser.add_argument("-f", "--file", required=True, type=str, help="data file")
    parser.add_argument("--true", required=True, type=str, help="list of repo links cited as created")
    parser.add_argument("--false", required=True, type=str, help="list of repo links that are just mentioned")
    parser.add_argument
    args = parser.parse_args()
    main(args.file, args.true, args.false)
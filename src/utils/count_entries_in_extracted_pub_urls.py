import os
import argparse
import pandas as pd

def main(dirpath):
    for f_path in sorted(os.listdir(dirpath)):
        if f_path.endswith(".csv"):
            print("File:", f_path)
            df = pd.read_csv(os.path.join(dirpath, f_path))
            print("Entries:", len(df))
            print("PDFs:", len(df[df['pdf_url'].str.endswith(".pdf")]))
            print("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="count_entries_in_extracted_pub_urls",
        description="For each CSV file in the directory, report the number of non-null entries in the relevant columns."
    )
    parser.add_argument("-d", "--directory", type=str,
                        help="Directory containing CSV files with publication URLs, one for each ePrints repository",
                        default="../../data/raw/eprints/publication_urls/")
    args = parser.parse_args()
    main(args.directory)
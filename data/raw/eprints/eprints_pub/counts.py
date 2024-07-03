import os
import pandas as pd

for f_path in sorted(os.listdir(".")):
    if f_path.endswith(".csv"):
        print("File:", f_path)
        df = pd.read_csv(f_path)
        print("Entries:", len(df))
        print("PDFs:", len(df[df['pdf_url'].str.endswith(".pdf")]))
        print("\n")
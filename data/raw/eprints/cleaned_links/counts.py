import pandas as pd

df = pd.read_csv("joined.csv")
for e_r in sorted(df.eprints_repo.unique()):
    print("Repo:", e_r)
    df_temp = df[df.eprints_repo == e_r]
    print("Links:", len(df_temp.domain_url.notna()))
    print("Pattern cleaned links:", len(df_temp.pattern_cleaned_url.notna()))
    print("User cleaned links:", len(df_temp.github_user_cleaned_url.notna()))
    print("Unique links:", len(df_temp.github_user_cleaned_url.unique()))
    print("\n")
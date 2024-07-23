#!/bin/bash

file="/home/kmoraw/SSI/rse-repo-analysis/data/derived/high_interest_repos.txt"
while read line; do
    python3 repository_timeline_anon_for_poster.py --repo "${line}" --outdir /home/kmoraw/SSI/rse-repo-analysis/data/derived/plots/repo_timelines/true_positives/many_users/
done < "${file}"

file="/home/kmoraw/SSI/rse-repo-analysis/data/derived/one_person_repos.txt"
while read line; do
    python3 repository_timeline_anon_for_poster.py --repo "${line}" --outdir /home/kmoraw/SSI/rse-repo-analysis/data/derived/plots/repo_timelines/true_positives/one_user/
done < "${file}"


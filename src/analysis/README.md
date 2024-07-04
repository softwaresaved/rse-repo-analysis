# `src/analysis`

The scripts in this directory were used to produce derived data and plots.

- [`aggregate_datasets.py`](./aggregate_datasets.py) aggregates all data mined from GitHub into four datasets described in the wiki. Crucially, the data is reshaped into a time-indexed format for three of those datasets.
- [`mention_type_timeline.py`](./mention_type_timeline.py) visualises the relationship between how a repository is cited and the difference between its creation date and the publication date.
- [`repo_intent.py`](./repo_intent.py) creates a dataset with all repositories mined from ePrints for which we manually determined the citation type. The resulting dataset contains data from ePrints as well as a label indicating whether the software was cited as created software.
- [`overall.py`](./overall.py)
- [`repository_timeline.py`](./repository_timeline.py)

The schemas for any produced datasets are included in the wiki.
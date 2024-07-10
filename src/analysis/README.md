# `src/analysis`

The scripts in this directory were used to produce derived data and plots.

- [`aggregate_datasets.py`](./aggregate_datasets.py) aggregates all data mined from GitHub into four datasets described in the wiki. Crucially, the data is reshaped into a time-indexed format for three of those datasets.
- [`mention_type_timeline.py`](./mention_type_timeline.py) visualises the relationship between how a repository is cited and the difference between its creation date and the publication date.
- [`repo_intent.py`](./repo_intent.py) creates a dataset with all repositories mined from ePrints for which we manually determined the citation type. The resulting dataset contains data from ePrints as well as a label indicating whether the software was cited as created software.
- [`overall.py`](./overall.py) creates one plot containing visualisations and data about all repositories. The dataset can be filtered for a subset of repositories with the `--filter` argument.
- [`repository_timeline.py`](./repository_timeline.py) creates one plot for one repository, focussing on timelined data. The code to produce these uses the raw data rather than the aggregated data produced by [`aggregate_datasets.py`](./aggregate_datasets.py) as this script was written before [`aggregate_datasets.py`](./aggregate_datasets.py). Both scripts use the same data manipulation methods - directly plotting data produced by [`aggregate_datasets.py`](./aggregate_datasets.py) should result in similar graphs.
- [`github.ipynb`](./github.ipynb) was used for exploratory data analysis. The most interesting visualisations were later transferred into `overall.py` and `repository_timeline.py`.
- [`eprints.ipynb`](./eprints.ipynb) produces visualisations illustrating the relationship between publications and GitHub links found in them.

The schemas for any produced datasets are included in the wiki.
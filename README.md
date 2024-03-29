# RSE Repository Analysis

Study of research software in repositories. Contact: @karacolada

## About this project

We want to investigate how research software projects have changed over time, how they evolve and how they differ between disciplines by analysing relevant software repositories.
This will help us gain a better understanding of ongoing processes in the research software community and of how they can be supported.
It will also supply evidence about which practices aid to build and maintain software with a wider community engagement.

We consider multiple approaches to finding relevant software repositories:
- existing datasets about software mentions in research (e.g. [CZI Software Mentions](https://github.com/chanzuckerberg/software-mentions), [Softcite Dataset](https://github.com/howisonlab/softcite-dataset))
- crawling publicly available publications for in-text Git(Hub) links (e.g. [ePrints](https://www.eprints.org/uk/))

### Hypothesis

The following is not meant to be a fixed set of things we want to find, but rather some ideas that may help guide what data is worth collecting.
We hypothesise that

1. research software repositories evolve in four stages
   1. no engagement: sparse commits, no issues, few authors, no license, no DOI citation
   2. publication: DOI, license, usage guidelines, some watchers/stars, some issues created and resolved by repository maintainers
   3. low engagement: external users create issues, maintainers resolve issues, forks
   4. community engagement: external users create and resolve issues, merge requests
2. research software repositories that employ good practices reach higher stages (earlier)

### Indicators

This list of indicators is meant for brainstorming. Not all data listed here will be collected in the end.

- Issues: can be queried using GitHub API, naturally show timeline of repository. Interesting first data points might be creation date, creator, resolver, closing date. Interesting future data points might be labels, linked merge requests.
- Commits: can be queried using GitHub API, naturally show timeline of repository. Rather than the commit contents, we would be more interested in the metadata (author, date) to deduce commit frequency and team dynamics.
- Content history: we might be able to gather this data from Git commits to a specific file (license, README, contributing). Interesting data points might be the date when it got added, and in case of the README, section titles and when they were updated as well as the presence of a DOI and whether that DOI is CrossRef (paper) or DataCite (dataset, software).
- Engagement history: Forks, Watchers, Stars. GitHub API will only return info about the current stats, but GitHub Archive or GitTorrent might be a helpful resource.

### Contextual Metadata

To contextualise the result, we should try and record information about the initial publication. This can then be used to find the publication on CrossRef etc. and collect further information such as:

- affiliation
- mention of developers to the software as authors of the publication
- topic

## Getting started

Clone this repository, then fetch the submodules:

```bash
cd rse-repo-analysis
git submodule init
git submodule update
```

### Layout

This project is in active development, so expect the file structure to change from time to time. 
- [`software-mentions`](software-mentions/): submodule containing a [fork](https://github.com/karacolada/software-mentions) of the Chan Zuckerberg Initiative's [Software Mentions Repository](https://github.com/chanzuckerberg/software-mentions)
  - [`SSI-notebooks`](software-mentions/SSI-notebooks/): our own scripts handling the CZI Software Mentions dataset
- [`eprints`](eprints/): source files for extracting URLs from papers publicly available in ePrints repositories

### Requirements

As this project is developed using Python, it is recommended to set up a new virtual environment, e.g. using [Conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).
Inside the environment, install the following packages:
- `pandas`
- `Jupyter`
- `matplotlib`
- [`PyGithub`](https://pygithub.readthedocs.io/en/latest/) for access to the GitHub API
- [`lxml`](https://lxml.de) for parsing XMLs
- [`pdfminer.six`](https://pdfminersix.readthedocs.io/en/latest/) for parsing PDFs
  - not to be confused with [`pdfminer`](https://github.com/euske/pdfminer), which is no longer actively maintained
- [`pySpark`](https://spark.apache.org)
  - depends on Java (e.g. OpenJDK)
  - depends on `pyarrow`
- [`emoji`](https://carpedm20.github.io/emoji/docs/)
- `Levenshtein`
- `unidecode`
- `pydriller`
- `wordcloud`
- `seaborn`
- `tol_colors`

#### GitHub API

It is advised to create an access token to authorise with the GitHub API, otherwise you will quickly run into the requests limit.
You can create a token [here](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-personal-access-token-classic).
Scripts making use of the GitHub API in this project will usually check for a file called `config.cfg` and expect your access token to be in there.
As access tokens should be kept secret, files named `config.cfg` will not be tracked by Git.

To provide the code with your access token, simply create a copy of [`config_example.cfg`](config_example.cfg), fill in your data and rename the copy to `config.cfg`.
This file should be located in the root directory of this repository, but you might also need a copy of it in the [`software-mentions`](software-mentions/) directory if you want to work with the code in the submodule.

#### Datasets

Depending on what you are trying to do, you will need to download datasets and place them in the correct spot of the repository.
This might be changed to configurable paths in the future, but for now, that is out of scope.

##### CZI Dataset

The code in [`software-mentions`](software-mentions/) expects the CZI dataset in its root directory, i.e. `software-mentions/data`.
You can download the dataset [here](https://datadryad.org/stash/dataset/doi:10.5061/dryad.6wwpzgn2c) and extract it into the correct location.

## Usage

ePrints:
- [`eprints/parse_eprints.py`](eprints/parse_eprints.py): Download XML data from an ePrints repository, perform a free-text search for any text containing the specified domain. Pass flag `--local` if you have already downloaded the XML data and want to process it locally.
- [`eprints/clean_eprints_links.py`](eprints/clean_eprints_links.py): Process extracted links using pattern matching and, optionally, user matching to ensure the extracted links are correct and reachable.
- [`extract_links_from_eprints.sh`](eprints/extract_links_from_eprints.sh): Executes both scripts.

GitHub (see also [GitHub API](#github-api)):
- [`github/crawl.py`](github/crawl.py): Takes CSV file and column name as argument. Crawls GitHub for info on the repositories named in the CSV file (issues, commits, contents) and stores them in a CSV file.

Utilities:
- [`utilities/create_representative_set_github.py`](utilities/create_representative_set_github.py): As the name suggests, samples a set of 100 GitHub repositories (not specifically research software) based on the number of stars a repository has. Produces a distribution of different repository sizes and forks. Useful for testing GitHub crawling code and estimating resulting dataset sizes.

### Data

Data is collected into [`data`](data/). Scripts will assume that all data collected in previous stages of the analysis are located here.

## References

Here, we list some works that we make use of.

### CZI Software Mentions
  
```
Istrate, A. M., Li, D., Taraborelli, D., Torkar, M., Veytsman, B., & Williams, I. (2022). A large dataset of software mentions in the biomedical literature. arXiv preprint arXiv:2209.00693.
```
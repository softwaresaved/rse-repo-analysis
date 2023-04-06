# RSE Repository Analysis

Study of research software in repositories. Contact: @karacolada

## About this project

We want to investigate how research software projects have changed over time and differ between disciplines by analysing relevant software repositories.
This will help us gain a better understanding of ongoing processes in the research software community and of how they can be supported.

We consider multiple approaches to finding relevant software repositories:
- existing datasets about software mentions in research (e.g. [CZI Software Mentions](https://github.com/chanzuckerberg/software-mentions), [Softcite Dataset](https://github.com/howisonlab/softcite-dataset))
- crawling publicly available publications for in-text Git(Hub) links (e.g. [ePrints](https://www.eprints.org/uk/))

Potentially interesting data points:
- licence
- team size
- commit frequency
- linkage to other research outputs
- topic
- maintenance time
- engagement (forks, stars, watchers)

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
# `src/ePrints`

Crawling ePrints repositories for links to git repositories. Run any script with `--help` to get more info on options and arguments.

Steps: 

1. For each ePrints repository, run [`parse_eprints.py`](./parse_eprints.py). This requests an XML list of ePrints publications and parses any links to downloadable files for those publications, including (but not limited to) PDFs.
2. For each ePrints repository, run [`parse_pdfs.py`](./parse_pdfs.py), which will try to parse any downloadable files identified in the previous step and extract any links to the specified domain (e.g. `github.com`).
3. The extracted links will likely be messy. Run [`clean_eprints_links.py`](./clean_eprints_links.py) to clean them through pattern matching and GitHub API queries (the latter only if the links are actually GitHub links). GitHub links will only be stored if they can be accessed via API without errors. 
4. Finally, [`merge_and_filter.py`](./merge_and_filter.py) can be used to merge all cleaned datasets into one dataframe and select only those links found on the first two pages.

# ePrints

Crawling ePrints repositories for links to git repositories.

Scripts:

- [`parse_eprints.py`](parse_eprints.py): Requests XML list of ePrints publications, parses links of a domain from PDFs available for download. Run with `--help` to get more info on options and arguments.
- [`clean_eprints_links.py`](clean_eprints_links.py): Goes through links found by parsing script and cleans them through pattern matching and GitHub API queries (the latter only if the links are actually GitHub links). GitHub links will only be stored if they can be accessed via API without errors. Run with `--help` to get more info on options and arguments.
- [`extract_links_from_eprints.sh`](extract_links_from_eprints.sh): Convenience script running the above scripts for the Southhampton ePrints repository, mostly used for testing.

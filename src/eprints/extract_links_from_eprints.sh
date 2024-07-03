#!/bin/bash

python3 parse_eprints.py --repo eprints.soton.ac.uk --date 2022- --domain github.com --local
python3 clean_eprints_links.py --repo eprints.soton.ac.uk --date 2022- --domain github.com --verbose
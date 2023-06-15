import requests
import re
import argparse
import resource
import pandas as pd
from io import BytesIO
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

def get_domain_urls(row, domain, verbose):
    """Yields matches of URLs of the domain in the PDF.

    Args:
        row (pd.Series): contains columns for PDF url
        domain (str): domain to scan for, e.g. github.com

    Returns:
        pd.Series: added columns ['page_no', 'domain_url']
    """
    pattern = rf"(?P<url>https?://(www\.)?{re.escape(domain)}[^\s]+)"
    matches = {k: [] for k in ['page_no', 'domain_url']}
    pdf = requests.get(row['pdf_url'], stream=True)
    if pdf.status_code == 200 and "pdf" in pdf.headers['content-type'] and int(pdf.headers['content-length']) < 5e7:  # ignore files larger than 50 MB to avoid OOM error
        if verbose:
            print(f"Parsing {row['pdf_url']} of size {int(pdf.headers['content-length'])}")
        try:
            page_layouts = extract_pages(BytesIO(pdf.content))
            for page_no, page_layout in enumerate(page_layouts):
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        text = element.get_text()
                        for match in re.finditer(pattern, text):
                            matches['page_no'].append(page_no)
                            matches['domain_url'].append(match.group("url"))
        except Exception:
            pass
    elif pdf.status_code == 200 and "pdf" in pdf.headers['content-type']:
        if verbose:
            print(f"Ignoring {row['pdf_url']} of size {int(pdf.headers['content-length'])}")
    for k, v in matches.items():
        row[k] = v
    return row

def main(repo, date, domain, verbose):
    path = f"../data/extracted_pdf_urls_{repo}_{date}.csv"
    df = pd.read_csv(path)
    d = df.apply(get_domain_urls, axis=1, args=(domain, verbose))
    print(d.head())
    if verbose:
        print(f"Extracted URLs of domain {domain} from respository {repo}.")
    d = d.dropna().explode(['page_no', 'domain_url'])
    d.dropna(axis=0, how='all', subset=['domain_url'], inplace=True)
    d.to_csv(f"../data/extracted_urls_{repo}_{date}_{domain}.csv", index=False)
    if verbose:
        print(f"Saved extracted URLs in ../data/extracted_urls_{repo}_{date}_{domain}.csv")

if __name__ == "__main__":
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (2000000000, hard))
    parser = argparse.ArgumentParser(
        prog="parse_pdfs",
        description="Scan the downloadable publications for links of a specific domain name, e.g. github.com."
    )
    parser.add_argument("--repo", required=True, type=str, help="name of ePrints repository (i.e. domain)")
    parser.add_argument("--date", required=True, type=str, help="date range for filtering ePrints, e.g. 2021-2022")
    parser.add_argument("--domain", required=True, type=str, help="domain to match against (only one can be provided for now, e.g. github.com)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.repo, args.date, args.domain, args.verbose)
import requests
from lxml import etree
import argparse
import pandas as pd

def get_paper_list(repo, date, path):
    """Sends request to repository for papers in the specified date range. Writes output to XML file.

    Args:
        repo (str): domain name of ePrints repository
        date (str): date range to consider
        path (str): path to write XML data to
    """
    request = f"https://{repo}/cgi/search/archive/advanced?screen=Search&" \
                "output=XML&" \
                "_action_export_redir=Export&" \
                "dataset=archive&" \
                "_action_search=Search&" \
                "documents_merge=ALL&" \
                "documents=&" \
                "eprintid=&" \
                "title_merge=ALL&" \
                "title=&" \
                "contributors_name_merge=ALL&" \
                "contributors_name=&" \
                "abstract_merge=ALL&" \
                "abstract=&" \
                f"date={date}&" \
                "keywords_merge=ALL&" \
                "keywords=&" \
                "divisions_merge=ANY&" \
                "pres_type=paper&" \
                "refereed=EITHER&" \
                "publication%2Fseries_name_merge=ALL&" \
                "publication%2Fseries_name=&" \
                "documents.date_embargo=&" \
                "lastmod=&" \
                "pure_uuid=&" \
                "contributors_id=&" \
                "satisfyall=ALL&" \
                "order=contributors_name%2F-date%2Ftitle"
    response = requests.get(request)
    with open(path, "wb") as f:
        f.write(response.content)

def get_specific_fields_content(element, field_name):
    """Returns content of XML fields of a specific name of an element.

    Args:
        element (lxml.etree._Element): XML element to analyse
        field_name (str): name of field to look for

    Returns:
        list<str>: list of contents found in children of element of given name
    """
    contents = []
    for child in list(element):
        if field_name == etree.QName(child.tag).localname:
            contents.append(child.text)
    return contents

def get_specific_fields_elements(element, field_name):
    """Returns XML subelements of the given element with the given name.

    Args:
        element (lxml.etree._Element): XML element to analyse
        field_name (str): name of field to look for

    Returns:
        list<lxml.etree._Element>: list of children found of the given name
    """
    elements = []
    for child in list(element):
        if field_name == etree.QName(child.tag).localname:
            elements.append(child)
    return elements

def parse_pdf_urls(path):
    """Extracts download URLs of PDFs from XML file.

    Args:
        path (str): path to XML file

    Yields:
        dict: contains title, download URL for PDF, name of one of the authors
    """
    with open(path, "rb") as f:
        tree = etree.parse(f)
    root = tree.getroot()
    children = list(root)
    for c in children:
        urls = []
        title = get_specific_fields_content(c, "title")[0]
        date = get_specific_fields_content(c, "date")[0]
        creators = get_specific_fields_elements(c, "creators")
        try:
            author_for_reference = get_specific_fields_elements(get_specific_fields_elements(creators[0], "item")[0], "name")[0]
            author_name_for_reference = f"{get_specific_fields_content(author_for_reference, 'given')[0]} {get_specific_fields_content(author_for_reference, 'family')[0]}"
        except IndexError:
            print(f"No athor found for {title}.")
            author_name_for_reference = ""
        documents_holders = get_specific_fields_elements(c, "documents")
        for documents_list in documents_holders:
            documents = get_specific_fields_elements(documents_list, "document")
            for document in documents:
                files_holders = get_specific_fields_elements(document, "files")
                for files_list in files_holders:
                    files = get_specific_fields_elements(files_list, "file")
                    for file in files:
                        urls += get_specific_fields_content(file, "url")
        if len(urls) > 0:  # NOTE: can sometimes include jpegs, docx etc.
            n = len(urls)
            yield {"title": [title for _ in range(n)], "date": [date for _ in range(n)], "url": urls, "author_for_reference": [author_name_for_reference for _ in range(n)]}

def main(repo, date, local, verbose):
    path = f"../data/export_{repo}_{date}.xml"
    if not local:
        get_paper_list(repo, date, path)
        if verbose:
            print("Downloaded XML list of publications.")
    pdf_dict = {'title': [], 'date': [], 'author_for_reference': [], 'pdf_url': []}
    for temp_dict in parse_pdf_urls(path):
        pdf_dict['title'] += temp_dict['title']
        pdf_dict['date'] += temp_dict['date']
        pdf_dict['author_for_reference'] += temp_dict['author_for_reference']
        pdf_dict['pdf_url'] += temp_dict['url']
    if verbose:
        print(f"Extracted PDF download URLs from respository {repo}.")
    df = pd.DataFrame(pdf_dict)
    df.drop_duplicates(subset=['pdf_url'], inplace=True)
    df.dropna(inplace=True)
    df.to_csv(f"../data/extracted_pdf_urls_{repo}_{date}.csv", index=False)
    if verbose:
        print(f"Saved extracted URLs in ../data/extracted_pdf_urls_{repo}_{date}.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="parse_eprints",
        description="Query ePrints repository for publications, extract PDF download URLs.."
    )
    parser.add_argument("--repo", required=True, type=str, help="name of ePrints repository (i.e. domain)")
    parser.add_argument("--date", required=True, type=str, help="date range for filtering ePrints, e.g. 2021-2022")
    parser.add_argument("--local", action="store_true", help="use local ePrints XML output instead of downloading from web")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    args = parser.parse_args()
    main(args.repo, args.date, args.local, args.verbose)
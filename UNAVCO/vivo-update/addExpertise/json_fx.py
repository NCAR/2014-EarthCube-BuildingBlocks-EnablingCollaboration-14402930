
def parse_publication_date(doi_record):
    date_parts = doi_record["issued"]["date-parts"][0]
    return date_parts[0], date_parts[1] if len(date_parts) > 1 else None, date_parts[2] if len(date_parts) > 2 else None


def parse_authors(doi_record):
    authors = []
    for author in doi_record["author"]:
        authors.append((author["given"], author["family"]))
    return authors

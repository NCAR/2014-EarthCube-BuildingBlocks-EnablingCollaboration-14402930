
def parse_publication_date(doi_record):
    if doi_record["issued"]["date-parts"]:
        date_parts = doi_record["issued"]["date-parts"][0]
        return date_parts[0], date_parts[1] if len(date_parts) > 1 else None, date_parts[2] if len(date_parts) > 2 else None
    else:
        return None

def parse_authors(doi_record):
    authors = []
    for author in doi_record["author"]:
        if "given" in author:
            authors.append((author["given"], author["family"]))
        elif "family" in author:
            authors.append((None, author["family"]))
        elif "literal" in author:
            #split up name if it's all one
            given_name = author["literal"].rsplit(' ',1)[0]
            family_name = author["literal"].rsplit(' ',1)[1]
            authors.append((given_name, family_name))
    return authors

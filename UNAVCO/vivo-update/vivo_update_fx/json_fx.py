
def parse_publication_date(doi_record):
    date_parts = doi_record["issued"]["date-parts"][0]
    return date_parts[0], date_parts[1] if len(date_parts) > 1 else None, date_parts[2] if len(date_parts) > 2 else None


def parse_authors(doi_record):
    authors = []
    if doi_record["creator"]:
        for author in doi_record["creator"]:
            #print(author)
            if ', ' in author: #last name first (probably)
                given_name = author.rsplit(', ',1)[1]
                family_name = author.rsplit(', ',1)[0]
                authors.append((given_name, family_name))
            else:
                # split up name if it's all one
                # TLS datasets are often like this
                given_name = author.rsplit(' ',1)[0]
                if 'Dr. ' in given_name:
                    given_name = given_name.replace('Dr. ','',1)
                    print(author + ' first name parsed as ' + given_name)
                family_name = author.rsplit(' ',1)[1]
                authors.append((given_name, family_name))

    return authors

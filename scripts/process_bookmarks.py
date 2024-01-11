import json
import os

import pandas as pd
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import requests
from lxml.html import fromstring
from pandas import CategoricalDtype


def getTitle(site):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'}
        response = requests.get(site, headers=headers, timeout=50)

        tree = fromstring(response.content)
        return tree.findtext('.//title')

    except Exception as e:
        print(f"Error retrieving page {site}\n\n{e}")
    return ''


def main():
    marks = json.load(open("../data/bookmarks.json", encoding="utf-8"))
    marks = marks['collections']['bookmarks']['records']

    incomingBookmarks = pd.DataFrame(marks)

    incomingBookmarks = incomingBookmarks.loc[incomingBookmarks['parentName'] == 'mobile']
    incomingBookmarks = incomingBookmarks[['bmkUri', 'title', 'dateAdded']]

    key = incomingBookmarks['bmkUri'].apply(lambda x: hashlib.sha256(x.encode('UTF-8')).hexdigest())
    incomingBookmarks.insert(0, "key", key)

    existingDB = "../data/bookmarks.db.json"

    marks = ''
    existingBookmarks = None
    if Path(existingDB).exists():
        try:
            marks = json.load(open(existingDB, encoding='utf-8'))
            print("Loading marks")
            existingBookmarks = pd.DataFrame(marks)
        except json.decoder.JSONDecodeError as e:
            # starting with empty bookmarksmarks db
            print("Generating marks")
            columns = list(incomingBookmarks.columns.values)
            columns += ["siteTitle", "siteIcon", "category", "domain", 'articleTitle']
            existingBookmarks = pd.DataFrame(columns=columns)

    categoryType = CategoricalDtype(categories=["A", "S", "O", "D"], ordered=True)
    existingBookmarks["category"] = existingBookmarks["category"].astype(categoryType)

    # remove all bookmarks previously processed
    newBookmarks = incomingBookmarks[~incomingBookmarks['key'].isin(existingBookmarks['key'].values)]
    if newBookmarks.empty:
        print("No new bookmarks to add")

    # gather the site info for existing bookmarks
    domains = dict()
    for domain in existingBookmarks['domain']:
        if domain is None:
            # find a cleaner way to do this using the query
            continue

        # load site info from an existing record
        siteInfo = existingBookmarks.loc[existingBookmarks['domain'] == domain].iloc[0]

        domains.update({
            domain: {
                'siteTitle': siteInfo['siteTitle'],
                'siteIcon': siteInfo['siteIcon']
            }
        })

    # add all new bookmarks to the bookmark set
    existingBookmarks = pd.concat([existingBookmarks, newBookmarks])

    # process all new bookmarks (and any that have not been processed before)
    processBookmarks = existingBookmarks[existingBookmarks['category'].isna()]

    existingBookmarks.set_index(['key'], inplace=True)
    processBookmarks.set_index(['key'], inplace=True)

    count = 1
    for i, mark in processBookmarks.iterrows():
        os.system('cls')
        print(f"\n\nProcessing {count} of {len(processBookmarks)} new bookmarks")
        print(f"URI: {mark['bmkUri']}")
        count += 1
        xmark = 'X'
        domain = f"{urlparse(mark['bmkUri']).netloc}"
        mark['domain'] = domain
        if domain not in domains:
            xmark = ''
            domains[domain] = {'siteTitle': '', 'siteIcon': ''}
            site = f"{urlparse(mark['bmkUri']).scheme}://{domain}/"

            domains[domain]['siteTitle'] = getTitle(site)

            # could get more robust and look for alt icons
            iconFile = site + "favicon.ico"
            try:
                if requests.head(iconFile).status_code == 200:
                    domains[domain]['siteIcon'] = iconFile
            except requests.exceptions.ConnectionError as e:
                print(f"Error retrieving site Icon {iconFile}\n\n{e}")

        mark['domain'] = domain
        mark['siteIcon'] = domains[domain]['siteIcon']
        mark['siteTitle'] = domains[domain]['siteTitle']
        mark['articleTitle'] = getTitle(mark['bmkUri'])


        print(f"Site: {urlparse(mark['bmkUri']).scheme}://{domain}/ -[{xmark}]")
        print(f"SiteTitle: {mark['siteTitle']}")
        print(f"Title: {mark['articleTitle']}")


        category = ''
        while not category:
            c = input('Category [A] AI/ML, [S] Software, [D] DELETE, [O] Other [Q] Quit):> [A] ').upper()
            if c not in ['', 'A', 'S', 'O', 'Q', 'D']:
                continue
            if c == '':
                c = 'A'
            category = c
        if category == 'Q':
            break

        mark['category'] = category


        # update the bookmarks db (in memory) with new values
        existingBookmarks.loc[i] = mark

    # save the changes
    existingBookmarks.reset_index(inplace=True)
    existingBookmarks.to_json(existingDB)



if __name__ == '__main__':
    main()

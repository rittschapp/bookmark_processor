import json
import os

import pandas as pd
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import requests
from lxml.html import fromstring
from pandas import CategoricalDtype

incomingBookmarksFile = "../data/bookmarks.json"
existingBookmarksFile = "../data/bookmarks.db.json"
promptString = "Category [A] AI/ML, [S] Software, [D] DELETE, [O] Other [Q] Quit):> [A] "
categories=["A", "S", "O", "D"]


def main():

    incomingBookmarks = loadIncomingBookmarks()

    existingBookmarks = loadExistingBookmarks(incomingBookmarks)

    # exclude not new
    newBookmarks = incomingBookmarks[~incomingBookmarks['key'].isin(existingBookmarks['key'].values)]
    if not newBookmarks.empty:
        print(f"Found {len(newBookmarks)} new bookmarks to add")

        # add all new bookmarks to the bookmark set
        existingBookmarks = pd.concat([existingBookmarks, newBookmarks])
        print(existingBookmarks.tail())

    processBookmarks(existingBookmarks)

    # save the changes
    existingBookmarks.to_json(existingBookmarksFile)


def getTitle(site):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'}
        response = requests.get(site, headers=headers, timeout=50)

        tree = fromstring(response.content)
        return tree.findtext('.//title')

    except Exception as e:
        print(f"Error retrieving page {site}\n\n{e}")
    return ''


def processBookmarks(existingBookmarks):

    # process all new bookmarks (and any that have not been processed before)
    bookmarksToProcess = existingBookmarks[existingBookmarks['category'].isna()]

    existingBookmarks.set_index(['key'], inplace=True)
    bookmarksToProcess.set_index(['key'], inplace=True)

    count = 1
    siteInfo = loadExistingSiteInfo(existingBookmarks)

    for i, mark in bookmarksToProcess.iterrows():
        os.system('cls')
        print(f"\n\nProcessing {count} of {len(bookmarksToProcess)} bookmarks")
        print(f"URI: {mark['bmkUri']}")
        count += 1
        xmark = 'X'
        uri = urlparse(mark['bmkUri'])
        domain = uri.netloc
        mark['domain'] = domain

        if domain not in siteInfo:
            xmark = ''
            siteInfo[domain] = getNewSiteInfo(uri)

        mark['siteIcon'] = siteInfo[domain]['siteIcon']
        mark['siteTitle'] = siteInfo[domain]['siteTitle']
        mark['articleTitle'] = getTitle(mark['bmkUri'])

        print(f"Site: {urlparse(mark['bmkUri']).scheme}://{domain}/ -[{xmark}]")
        print(f"SiteTitle: {mark['siteTitle']}")
        print(f"Title: {mark['articleTitle']}")

        category = ''
        while not category:
            c = input(f"{promptString} ").upper()
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

    existingBookmarks.reset_index(inplace=True)


def getNewSiteInfo(uri):
    domain = uri.netloc
    site = f"{uri.scheme}://{domain}/"
    siteInfo = {'siteTitle': getTitle(site), 'siteIcon': ''}
    # could get more robust and look for alt icons
    iconFile = site + "favicon.ico"
    try:
        if requests.head(iconFile).status_code == 200:
            siteInfo['siteIcon'] = iconFile
    except requests.exceptions.ConnectionError as e:
        print(f"Error retrieving site Icon {iconFile}\n\n{e}")
    return siteInfo

def loadExistingSiteInfo(existingBookmarks):
    # gather the site info for existing bookmarks
    siteInfo = dict()

    for domain in existingBookmarks['domain']:
        if domain is None or pd.isna(domain):
            continue

        # load site info from an existing record
        domainInfo = existingBookmarks.loc[existingBookmarks['domain'] == domain].iloc[0]

        siteInfo.update({
            domain: {
                'siteTitle': domainInfo['siteTitle'],
                'siteIcon': domainInfo['siteIcon']
            }
        })
    return siteInfo


def loadIncomingBookmarks():
    marks = json.load(open(incomingBookmarksFile, encoding="utf-8"))
    marks = marks['collections']['bookmarks']['records']
    incomingBookmarks = pd.DataFrame(marks)
    incomingBookmarks = incomingBookmarks.loc[incomingBookmarks['parentName'] == 'mobile']
    incomingBookmarks = incomingBookmarks[['bmkUri', 'title', 'dateAdded']]
    key = incomingBookmarks['bmkUri'].apply(lambda x: hashlib.sha256(x.encode('UTF-8')).hexdigest())
    incomingBookmarks.insert(0, "key", key)
    return incomingBookmarks


def loadExistingBookmarks(incomingBookmarks):
    marks = None
    if not Path(existingBookmarksFile).exists():
        # starting with new bookmarks using columns from incoming bookmarks file
        # and the new columns added by this script
        columns = list(incomingBookmarks.columns.values)
        columns += ["siteTitle", "siteIcon", "category", "domain", 'articleTitle']
        marks = pd.DataFrame(columns=columns)
    else:
        try:
            marks = json.load(open(existingBookmarksFile, encoding='utf-8'))
            marks =  pd.DataFrame(marks)
        except json.decoder.JSONDecodeError as e:
            # need to troubleshoot the error, adjust data or code
            print(f"Failed to load existing bookmarks file: {e}")
            exit(-1)
    marks["domain"] = marks["domain"].astype("string")
    categoryType = CategoricalDtype(categories=categories, ordered=True)
    marks["category"] = marks["category"].astype(categoryType)
    return marks


if __name__ == '__main__':
    main()

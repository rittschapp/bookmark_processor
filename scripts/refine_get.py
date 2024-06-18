import json
from requests.exceptions import HTTPError

import pandas as pd
from pandas import CategoricalDtype
import favicon

# simple script to get a website
# - siteTitle
# - siteIcon
# - articleTitle
#
# used to refine the accuracy of the process that gets this info for the
# bookmark processor

existingBookmarksFile = "../data/bookmarks.db.json"
categories = ["A", "S", "O", "D"]




def main():

    marks = json.load(open(existingBookmarksFile, encoding='utf-8'))
    df = pd.DataFrame(marks)

    domains = set()
    missing_values_df = df.loc[
        #(df['siteTitle'] == '') |
        #(df['siteTitle'] == 'Just a moment...') |
        #(df['siteTitle'] == 'Error 404 (Not Found)!!1') |
        (df['siteIcon'] == '')
        ]

    for i, row in missing_values_df.iterrows():
        domains.add(row.domain);

    print(len(domains))
    i = 1
    for domain in domains:

        print("~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-")
        print(f"{i} https://{domain}")
        i += 1

        #siteTitle = input("Site Title: ")
        try:
            siteImage = favicon.get(f"https://{domain}")[0]
            #fix = input(f"Fix {domain} \nsiteTitle: {siteTitle}\nsiteImage: {siteImage}\n>>> Y/N ? ")
            #    print(f"fixing {domain}")
            #    ##df.loc[df['domain'] == domain, 'siteTitle'] = siteTitle;
            df.loc[df['domain'] == domain, 'siteIcon'] = siteImage.url
            print(f"{domain} -> \n {siteImage.url}")
        except HTTPError as err:
            print(f"Some error with {domain} HTTP Code: {err.response.status_code}")

    df.to_json(existingBookmarksFile)





if __name__ == '__main__':
    main()



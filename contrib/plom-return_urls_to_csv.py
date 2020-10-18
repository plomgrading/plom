# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Colin B. Macdonald

"""Put Plom's return codes into a Canvas sheet for use with [1]

[1] https://github.com/ubccapico/sending-conversations

TODO: doesn't really need to be a Canvas sheet.
TODO: see below about using Plom's Canvas load functions.
"""

from pathlib import Path

import numpy as np
import pandas as pd

where_csv = Path('.')
in_csv = where_csv / 'latest_canvas_export.csv'
# created by plom-finish webpage --hex
return_codes_csv = where_csv / 'return_codes.csv'
out_csv = where_csv / 'classlist_return_links.csv'

basename = "253t1"
baseurl = "https://amcweb.math.ubc.ca/~cbm/return20w1/" + basename

df_return_codes = pd.read_csv(return_codes_csv, dtype="object")

# TODO: drop empty rows: too magical to hardcode, better to use:
#import plom.finish.return_tools import import_canvas_csv
#df = import_canvas_csv(...)
# TODO: or split out a filter_junk_rows function
df = pd.read_csv(in_csv, dtype="object")
print(df.head())
df = df.drop([df.index[0], df.index[1]])
df = df.reset_index(drop=True)
print(df.head())

df = pd.merge(df, df_return_codes, how="left", left_on="Student Number", right_on="StudentID")

def f(x):
    if pd.isnull(x['Return Code']):
        return x['Return Code']
    sid = x['Student Number']
    code = x['Return Code']
    return "{}/{}_{}_{}.pdf".format(baseurl, basename, sid, code)

df['test_return_url'] = df.apply(f, axis=1)

df.to_csv(out_csv, index=False)

# This script fetches the latest country statistics from pinballmap.com, 
# saves the data in JSON format, and tracks historical changes in a CSV file.

#%%
# Using the #%%-convention to get the best of both worlds (notebooks and plain scripts)
# https://jupytext.readthedocs.io/en/latest/formats-scripts.html#the-percent-format
import requests
import pandas as pd
import os
from datetime import datetime
import json
import shutil
import glob

#%%
# Fetch the latest country statistics from pinballmap.com
response = requests.get(
    url='https://pinballmap.com/api/v1/locations/countries.json'
)

assert(response.status_code == 200), f"Failed to retrieve data: {response.status_code}"

countries_json = response.json()

# %%
# Write the JSON data to a file in pretty print format
# Why pretty print? Because it diffs better in git.
with open('countries.json', 'w') as out_file:
     json.dump(countries_json, out_file, sort_keys = True, indent = 4)

# And stick it in the history folder with a timestamp, as well.
history_file_path = f'json-history/{datetime.now().strftime('%Y-%m-%d_')}countries.json'
os.makedirs('json-history', exist_ok=True)
shutil.copy('countries.json', history_file_path)

# %%
json_fnames = glob.glob('json-history/*.json')
countries_dfs = []
for fname in json_fnames:
    countries_df = (
        pd.read_json(fname)
        [["country", "location_count"]]
        # Pick the date from the filename
        .assign(fname=fname)
    ) 
    countries_dfs.append(countries_df)


# %%
countries_history = (
    pd.concat(countries_dfs)
    .assign(date=lambda x: pd.to_datetime(
        # The file name is the last part of the path ...            
        x['fname'].str.split('/').str[-1]
        # ... and the date is the first part of the filename
        .str.split('_').str[0])
    )
    .drop(columns='fname')
    .sort_values(['date', 'country'])
)

# %%
countries_history.to_csv('countries-history.csv', index=False)

# -------------------------------------------------------------------

# %%
# That concludes the neccecary steps to fetch and store the pinballmap's data
# buuuuut, let's also plot the timeseries for the top 10 current contries,
# just for the fun of it :) 

latest_date = countries_history['date'].max()

top_10_countries = (
    countries_history
    .query("date == @latest_date")
    .sort_values('location_count', ascending=False)
    .head(10)
    ["country"]
)

top_10_countries_history = (
    countries_history
    .query("country in @top_10_countries")
    .assign(country = lambda x: pd.Categorical(x['country'], categories=top_10_countries))
)

# %%
from plotnine import (
    ggplot,
    aes,
    geom_line,
    geom_point,
    labs,
    scale_x_datetime,
    scale_y_log10
)

top_10_countries_plot = (
    ggplot(top_10_countries_history, aes(x="date", y="location_count", color="country")) +
    geom_line() + 
    geom_point() +
    scale_x_datetime(date_breaks="1 month", date_labels="%Y %b") +
    scale_y_log10(labels=lambda x: x) +
    labs(
        title="Top 10 countries with most public pinball locations",
        subtitle=f"as of {latest_date.strftime('%Y-%m-%d')}",
        x="",
        y="Number of locations"
    )
)

top_10_countries_plot.save("top-10-countries.svg", width=7, height=4, verbose=False)

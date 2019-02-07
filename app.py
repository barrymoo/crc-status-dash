import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Event
import numpy as np
import os
import pandas as pd
import plotly.graph_objs as go
import pymongo


# For a cluster, query, filter, and return the data needed by plotly
def fill_dfs(cluster, limit):
    # Generate the Cursor/DataFrame (reversed)
    cursor = (
        db["status"]
        .find({"cluster": cluster})
        .sort("_id", pymongo.DESCENDING)
        .limit(limit)
    )
    df = pd.DataFrame.from_records(cursor).sort_index(axis=0, ascending=False)

    # Create the percent column, set any divbyzero (inf) to 0.0
    df["percent"] = 100 * df["allocated"] / df["total"]
    df.replace(np.inf, 0.0)

    # Return the df
    return df


# Generate an html.Tr list
def generate_html_tr(cluster):
    return [html.Tr([html.Td(x) for x in get_table_entry(cluster)])]


# Generate the table which prints the cluster, allocated and total cores
# -> I had a hard time figuring out how to write an additional list comprehension
# ->  to deal with the loop over each cluster
def generate_table():
    return html.Table(
        # Header
        [html.Tr([html.Th(x) for x in ["Cluster", "Used Cores", "Total Cores"]])]
        +
        # Body
        generate_html_tr("smp")
        + generate_html_tr("gpu")
        + generate_html_tr("mpi")
        + generate_html_tr("htc")
    )


# For the table, I only need one entry from the database
def get_table_entry(cluster):
    cursor = (
        db["status"].find({"cluster": cluster}).sort("_id", pymongo.DESCENDING).limit(1)
    )
    for item in list(cursor):
        return cluster, item["allocated"], item["total"]


# Get all the data to build our plot, also clean out any data points
# -> which are not shared by each cluster
def generate_figure():
    # Get the DF's
    smp = fill_dfs("smp", limit)
    gpu = fill_dfs("gpu", limit)
    mpi = fill_dfs("mpi", limit)
    htc = fill_dfs("htc", limit)

    # Concat the DF's together
    # -> We use the 'time' column because any missing entries will get set
    # -> to NaN. Then, we can just remove the rows with any NaNs
    concat = pd.concat(
        [
            smp.set_index("time"),
            gpu.set_index("time"),
            mpi.set_index("time"),
            htc.set_index("time"),
        ],
        axis="columns",
        keys=["smp", "gpu", "mpi", "htc"],
    )
    concat.dropna(inplace=True)
    concat["time"] = concat.index.to_series()

    # Generate the Traces
    traces = [
        go.Scatter(
            x=concat["time"],
            y=concat[cluster]["percent"],
            name=cluster,
            mode="lines+markers",
        )
        for cluster in ["smp", "gpu", "mpi", "htc"]
    ]
    layout = go.Layout(
        title="Cluster Status",
        titlefont={"size": 18},
        yaxis={
            "ticksuffix": "%",
            "title": "Percent Utilization",
            "titlefont": {"size": 18},
            "tickfont": {"size": 18},
        },
        xaxis={
            "title": "Date (MM/DD/YY-HH:MM)",
            "nticks": 4,
            "titlefont": {"size": 18},
            "tickfont": {"size": 18},
        },
        legend={"font": {"size": 18}},
    )
    return {"data": traces, "layout": layout}


# The layout function, this allows for the page updates when navigating to the site
def generate_layout():
    return html.Div(
        children=[
            # html.H1(children = 'CRC Status'),
            dcc.Graph(id="crc-graph", figure=generate_figure()),
            html.Table(id="crc-table", children=generate_table()),
            dcc.Interval(id="interval-component", interval=5 * 60 * 1000),
        ]
    )


# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server
# -> This part is important for Heroku deployment
server.secret_key = os.environ["SECRET_KEY"]

# Ready the database
uri = os.environ["MONGO_URI"]
client = pymongo.MongoClient(uri)
db = client.get_default_database()

# The limit of datapoints to return
# -> I don't want more than 24 points at a time
limit = db["status"].find({"cluster": "smp"}).count()
if limit > 24:
    limit = 24

# The app layout w/ custom CSS for the table
app.layout = generate_layout
app.css.append_css({"external_url": "https://codepen.io/anon/pen/LjQejb.css"})

# Update the plot every interval tick
@app.callback(
    Output("crc-graph", "figure"), events=[Event("interval-component", "interval")]
)
def update_crc_graph():
    return generate_figure()


# Update the table every interval tick
@app.callback(
    Output("crc-table", "children"), events=[Event("interval-component", "interval")]
)
def update_crc_table():
    return generate_table()


# Our main function
if __name__ == "__main__":
    app.run_server()

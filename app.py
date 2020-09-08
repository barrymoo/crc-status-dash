import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import numpy as np
import os
import pandas as pd
import plotly.graph_objs as go
import pymongo


def query_data(limit):
    client = pymongo.MongoClient(uri)
    db = client.get_database()
    cursor = (
        db["status"]
        .find({})
        .sort("_id", pymongo.DESCENDING)
        .limit(limit)
    )
    df = pd.DataFrame.from_records(cursor).sort_index(axis=0, ascending=False)

    for idx, row in df.iterrows():
        for c in clusters:
            row[c]["percent"] = 100. * row[c]["alloc"] / row[c]["total"]
        df.loc[idx, :] = row
    df.replace(np.inf, 0.0)
    return df.loc[:, df.columns != "_id"].to_json()


# Generate an html.Tr list
def generate_html_tr(cluster, data):
    return [html.Tr([html.Td(x) for x in get_table_entry(cluster, data)])]


# Generate the table which prints the cluster, allocated and total cores I had
# a hard time figuring out how to write an additional list comprehension to
# deal with the loop over each cluster
def generate_table(data):
    return html.Table(
        # Header
        [html.Tr([html.Th(x) for x in ["Cluster", "Used Cores", "Total Cores"]])]
        +
        # Body
        generate_html_tr("smp", data)
        + generate_html_tr("gpu", data)
        + generate_html_tr("mpi", data)
        + generate_html_tr("htc", data)
    )


# For the table, I only need one entry from the database
def get_table_entry(cluster, data):
    df = pd.read_json(data)
    df["time"] = pd.to_datetime(df["time"], format="%m/%d/%y-%H:%M")
    df.sort_values(by=["time"], inplace=True)
    row = df.iloc[-1, :]
    return cluster, row[cluster]["alloc"], row[cluster]["total"]


# Get all the data to build our plot, also clean out any data points
# -> which are not shared by each cluster
def generate_figure(data):
    df = pd.read_json(data)
    df["time"] = pd.to_datetime(df["time"], format="%m/%d/%y-%H:%M")
    df.sort_values(by=["time"], inplace=True)

    # Generate the Traces
    traces = [
        go.Scatter(
            x=df["time"],
            y=df[c].apply(lambda x: x["percent"]),
            name=c,
            mode="lines+markers",
        )
        for c in clusters
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
def generate_layout(data):
    return html.Div(
        children=[
            # html.H1(children = 'CRC Status'),
            dcc.Graph(id="crc-graph", figure=generate_figure(data)),
            html.Table(id="crc-table", children=generate_table(data)),
            html.Div(id="data", style={"display": "none"}),
            dcc.Interval(
                id="interval-component",
                interval=300000,
                n_intervals=0,
            ),
        ]
    )


# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=["https://codepen.io/barrymoo/pen/rbaKVJ.css"],
)
server = app.server

# Ready the database
uri = os.environ["MONGO_URI"]
client = pymongo.MongoClient(uri)
db = client.get_database()

# The limit of datapoints to return
# -> I don't want more than 24 points at a time
limit = db["status"].count_documents({})
if limit > 24:
    limit = 24
del client
del db

clusters = ["smp", "gpu", "mpi", "htc"]

initial_data = query_data(limit)

app.layout = lambda: generate_layout(initial_data)


@app.callback(
    Output("data", "children"),
    [Input("interval-component", "n_intervals")],
)
def query_data_callback(_):
    return query_data(limit)


@app.callback(
    Output("crc-graph", "figure"),
    [
        Input("interval-component", "n_intervals"),
        Input("data", "children"),
    ],
)
def update_crc_graph(_, data):
    return generate_figure(data)


# Update the table every interval tick
@app.callback(
    Output("crc-table", "children"),
    [
        Input("interval-component", "n_intervals"),
        Input("data", "children"),
    ],
)
def update_crc_table(_, data):
    return generate_table(data)


# Our main function
if __name__ == "__main__":
    app.run_server()


import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import datetime
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

from dash.dependencies import Input, Output
from urllib.request import urlopen

###################
# App setup
###################

# Styling
external_stylesheets = [dbc.themes.FLATLY]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Rona Stats'


########
# Data
########

def grab_data():
    """
    Grab a CSV of Covid data from the web.

    :return (Dict of Pandas DataFrames) The data for each country.
    """
    URL_DATASET = r'https://raw.githubusercontent.com/datasets/covid-19/master/data/countries-aggregated.csv'
    covid_data = pd.read_csv(URL_DATASET)
    countries = {
        country: covid_data[covid_data["Country"] == country]
         for country in set(covid_data["Country"])}

    del countries['MS Zaandam']
    del countries['Diamond Princess']
    countries['South Korea'] = countries.pop('Korea, South')
    countries['Taiwan'] = countries.pop('Taiwan*')
    countries['Myanmar'] = countries.pop('Burma')
    countries['Côte d\'Ivoire'] = countries.pop('Cote d\'Ivoire')
    countries['Republic of the Congo'] = countries.pop('Congo (Brazzaville)')
    countries['DRC'] = countries.pop('Congo (Kinshasa)')

    return countries


def cumulative_to_daily(data):
    """
    Calculate the daily changes in the data for a single country.

    :param data (DataFrame) A Pandas DataFrame containing cumulative data for a single country.
    :return (DataFrame) Day-by-day data for the given country.
    """

    def daily_series(values):
        yesterday = pd.concat([pd.Series([0]), values.iloc[:-1]]
                              ).reset_index(drop=True)
        values = values.reset_index(drop=True) - yesterday
        return values

    data_daily = data.copy().reset_index(drop=True)
    data_daily['Confirmed'] = daily_series(data['Confirmed'])
    data_daily['Deaths'] = daily_series(data['Deaths'])
    data_daily['Recovered'] = daily_series(data['Recovered'])

    return data_daily


# Cumulative and daily data
country_dfs = grab_data()
country_dfs_daily = {k: cumulative_to_daily(v) for k, v in country_dfs.items()}

# Just the dates for the data.
dates = country_dfs['United Kingdom']['Date']

# Population data from 2020 for each country
populations = {item[1]["Country"]: item[1]["Population"] for item in pd.read_csv(
    './data/population-by-country-2020.csv').iterrows()}


##################################
# Line plot card
##################################


# Select country
dropdown_countries = dcc.Dropdown(
    id='countries',
    options=[
        {'label': country, 'value': country}
        for country in sorted(country_dfs)
    ],
    value=['United Kingdom', 'US', 'France'],
    multi=True,
)

# Select statistic
radio_stats = dbc.RadioItems(
    id='statistics',
    options=[
        {'label': 'Deaths', 'value': 'deaths'},
        {'label': 'Cases', 'value': 'cases'}
    ],
    value='deaths',
)

# Select display type
radio_display = dbc.RadioItems(
    id='display',
    options=[
        {'label': 'Cumulative', 'value': 'cumulative'},
        {'label': 'Daily', 'value': 'daily'}
    ],
    value='cumulative',
)

# Adjust for population?
checkbox_population = dbc.Checklist(
    id='checkbox_population',
    options=[
        {'label': 'Adjust for population', 'value': 'population'},
    ],
    value=[]
)

# Helper function for trace
def covid_data_trace(country, deaths, daily, population=False):
    data = country_dfs_daily[country] if daily else country_dfs[country]
    dates = [str(x) for x in country_dfs['US']['Date']]
    values = data['Deaths' if deaths else 'Confirmed']

    if population:
        values = values / populations[country]

    return go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        opacity=0.7,
        marker={
            'size': 15,
            'line': {'width': 0.5, 'color': 'blue'},
        },
        name=country
    )

# Helper function for trace layout
def covid_data_layout():
    return go.Layout(
        xaxis={'title': 'Date'},  # Don't use layout: linear
        yaxis={'title': 'Deaths'},
        margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
        hovermode='closest',
    )

# A graph
graph = dcc.Graph(
    id='covid_graph',
    figure={
        'data': [
            covid_data_trace(country='US', deaths=True, daily=False)
        ],
        'layout': covid_data_layout()
    }
)

# The main countries line chart
stats_card = dbc.Card(
    dbc.CardBody(
        [
            html.H4("Coronavirus worldwide statistics",
                    className="line-card-title"),

            # The controls
            dbc.Row([
                    dbc.Col([dropdown_countries], width=True),
                    dbc.Col([radio_stats],
                            className='col-12 col-sm-12 col-md-auto'),
                    dbc.Col([radio_display],
                            className='col-12 col-sm-12 col-md-auto')
                    ], className='container-fluid mb-2'),

            dbc.Row([
                dbc.Col([checkbox_population],
                        className='col-12 col-sm-12 col-md-auto')
            ]),

            # The graph
            graph
        ]
    ), className='mb-3'
)


##################################
# Map plot card
##################################

play_button = dbc.Button(
    'Play', id='play'
)

# Label to display slider value
slider_label = dbc.Label(
    dates.iloc[-1], id='slider_label'
)

# A date slider
marks = {}
for i in range(len(dates)):
    date = datetime.datetime.strptime(dates.iloc[i], '%Y-%m-%d')
    if date.day == 1:
        marks[i] = date.strftime("%B")

date_slider = dcc.Slider(
    id='date_slider',
    #min = datetime.datetime.strptime(dates.iloc[0], '%Y-%m-%d').timestamp(),
    #max = datetime.datetime.strptime(dates.iloc[-1], '%Y-%m-%d').timestamp(),
    #step = 10000,
    min=1,
    max=len(dates) - 1,
    value=len(dates) - 1,
    step=1,
    updatemode='drag',
    marks=marks,
    #tooltip = { 'placement': 'bottom' }
)

# The main map trace
def chloropleth_trace(index):
    return go.Choropleth(
        locations=[*country_dfs.keys()] + ['Turkmenistan'],
        locationmode='country names',
        z=[v['Confirmed'].iloc[index] for v in country_dfs_daily.values()] + [0],
        colorscale='matter',
        colorbar={'title': 'Cases of COVID-19'},
        zmin=0,
        zmax=max([v['Confirmed'].max() for v in country_dfs_daily.values()])
    )

# Layout for the map
def chloropleth_layout():
    return go.Layout(
        dragmode=False,
        mapbox_style='carto-positron',
        mapbox_zoom=3,
        mapbox_center={"lat": 37.0902, "lon": -95.7129},
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        geo={
            'showframe': False,
            'showcoastlines': False,
            'projection_type': 'equirectangular'
        },
    )

# A map plot
map_plot = dcc.Graph(
    id='map_plot',
    figure={
        'data': [
            chloropleth_trace(-1)
        ],
        'layout': chloropleth_layout(),
    }
)

# A map card
map_card = dbc.Card(
    dbc.CardBody(
        [
            html.H4("Coronavirus map (daily new cases)",
                    className="map-card-title"),
            dbc.Row([
                #dbc.Col([play_button], width='auto'),
                dbc.Col([slider_label], width='auto'),
                dbc.Col([date_slider], width=True)]),
            map_plot
        ]
    )
)


##################
# Callbacks
##################

@app.callback(
    Output('covid_graph', 'figure'),
    [
        Input('countries', 'value'),
        Input('statistics', 'value'),
        Input('display', 'value'),
        Input('checkbox_population', 'value')
    ]
)
def update_graph(countries, statistics, display, population_options):
    return {
        'data': [
            covid_data_trace(
                country=country,
                deaths=(statistics == 'deaths'),
                population=("population" in population_options),
                daily=(display == 'daily')
            )
            for country in countries
        ],
        'layout': covid_data_layout()
    }


@app.callback(
    Output('slider_label', 'children'),
    [
        Input('date_slider', 'value')
    ]
)
def update_date_label(date_index):
    return dates.iloc[date_index]


@app.callback(
    Output('map_plot', 'figure'),
    [
        Input('date_slider', 'value')
    ]
)
def update_chloropleth(value):
    return {
        'data': [chloropleth_trace(value)],
        'layout': chloropleth_layout()
    }


############################
# Construct and run the app
############################

# Add the two cards to a main div.
app.layout = html.Div([stats_card, map_card])

if __name__ == '__main__':
    app.run_server(debug=True)

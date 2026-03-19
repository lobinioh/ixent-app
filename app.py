#!/usr/bin/env python3

import io
import os
import json
import socket
import base64
import webbrowser
import plotly
import plotly.colors
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import waitress

import dash.dependencies
from dash.exceptions import PreventUpdate
from dash import Dash, html, dcc
app = Dash(__name__)


marker_size_min = 4
marker_size_max = 20
line_size_min = 1
line_size_max = 10

all_columns = list()
all_columns_filtered = list()
norm_el = list()
all_columns_colored = list()
all_columns_styled = list()
all_columns_markered = list()
row_iterator_filtered = list()
column_iterator_filtered = list()



########################################################################################################################
### This initially creates and arranges all the buttons and fields and other gui features
########################################################################################################################

app.layout = html.Div(id='tot_frame', children=[
    dcc.Store(id='data', data=pd.DataFrame().to_records()), # data matrix stored on server
    dcc.Store(id='file-names', data=list()), # list of filenames stored on server
    dcc.Store(id='settings-file', data=dict()), # settings file stored on server

    # subframe left side for menu bar
    html.Div(className='left_menu', children=[
        dcc.ConfirmDialogProvider(
            children=html.Img(
                id='logo',
                src=app.get_asset_url('ixent_logo_400.png'),
                style={
                    'display': 'block',
                    'maxWidth': '100%',
                    'height': 'auto',
                    'textAlign': 'center',
                    'margin': '0 auto'
                }
            ),
            id='confirm',
            message="What\'s up?"
        ),
        html.Div([
            html.Button(
                id='reset-data',
                n_clicks=0,
                children='RESET Data',
                style={"flex": "1", "marginRight": "2px"}
            ),
            html.Button(
                id="update-plot",
                n_clicks=0,
                children="UPDATE Plot",
                style={"flex": "1", "marginLeft": "2px"}
            ),
        ], style={"display": "flex", "width": "100%", "height":"30px"}),
        html.Br(),

        dcc.Upload(
            id='upload-data',
            children=html.Div(['Drag & Drop or ', html.A('Select Files')]),
            style={'width': '99%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px',
                   'borderStyle': 'dashed',
                   'borderRadius': '5px', 'textAlign': 'center', 'font-family': 'sans-serif'},
            multiple=True,  # Allow multiple files to be uploaded
            accept='text/csv, application/vnd.ms-excel' # might lead to errors when app is used on macOS
        ),
        html.Br(),
        dcc.Upload(
            id='upload-setting-file',
            children=html.Div(['Drag & Drop or Select .json Setting File']),
            style={'width': '99%', 'height': '60px', 'lineHeight': '60px', 'borderWidth': '1px',
                   'borderStyle': 'dashed',
                   'borderRadius': '5px', 'textAlign': 'center', 'font-family': 'sans-serif'},
            # Allow multiple files to be uploaded
            multiple=False,
            # might lead to errors when app is used on macOS
        ),
        html.Br(),
        # html.Label('Following files are loaded:'),
        dcc.Textarea(id='uploaded-files', value='No Files uploaded', disabled=True,
                     style={'width': '98%', 'height': '80px', 'font-family': 'sans-serif'}),

        html.Br(),
        html.Br(),
        html.Div([
            dcc.Input(
                id='download-name',
                value='',
                type='text',
                placeholder='Download Filename...',
                style={"flex": "5", "marginRight": "2px"}  # input takes more space
            ),
            html.Button(
                id='download-button-html',
                n_clicks=0,
                children='.html',
                style={"flex": "1", "marginRight": "4px"}
            ),
            dcc.Download(id='download-plot-html'),

            html.Button(
                id='download-button-csv',
                n_clicks=0,
                children='.csv',
                style={"flex": "1", "marginRight": "2px"}
            ),
            dcc.Download(id='download-dataframe-csv'),

            html.Button(
                id='download-settings-button',
                n_clicks=0,
                children='.json',
                style={"flex": "1", "marginLeft": "2px"}
            ),
            dcc.Download(id='download-settings-json'),
        ], style={
            "display": "flex",
            "width": "100%",
            "height": "30px"
        }),
        html.Div(id='download-state'),

        html.Br(),
        html.Hr(),
        html.Br(),

        # dropdown for x-values (single select)
        html.Label('x-axis data'),
        dcc.Dropdown(all_columns, id='x_tag', multi=False, placeholder='(required) Select the variable for the X-axis'),
        html.Br(),
        # dropdown for y-values (multi select possbile)
        html.Label('y-axis data (primary)'),
        dcc.Dropdown(all_columns, id='y_tags1', multi=True, placeholder='(required) Select the variable(s) for the Y-axis'),
        html.Br(),
        html.Label('y-axis data (secondary)'),
        dcc.Dropdown(all_columns, id='y_tags2', multi=True, placeholder='(optional) Select the variable(s) for the Y-axis'),
        html.Br(),
        html.Label('Colormap'),
        dcc.Dropdown(all_columns, id='colormap_column', multi=False, placeholder='(optional) Select the variable for colormap'),
        dcc.Dropdown(all_columns_filtered, id='colormap_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        # coarse filter
        html.Label('Filter criteria:'),
        dcc.Dropdown(all_columns, id='filter_column', placeholder='(optional) Select variable for filtering'),
        dcc.Dropdown(all_columns_filtered, id='filter_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Hr(),
        html.Br(),

        # another subframe with line type state and button
        html.Div([
            html.Div([
                html.Label('Plot style:'),
                dcc.RadioItems(
                    options=['line', 'marker', 'line & marker', 'histogram'],
                    value='line & marker',
                    id='line_mode',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ], style={"marginBottom": "10px"}),

            html.Div([
                html.Label('Differentiate multiple y-axis series by:'),
                dcc.RadioItems(
                    options=['color', 'line style', 'marker', 'none'],
                    value='none',
                    id='iter_criterion',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ], style={"marginBottom": "10px"}),

            html.Div([
                html.Label('Differentiate primary vs. secondary y-axis by:'),
                dcc.RadioItems(
                    options=['color', 'line style', 'marker', 'none'],
                    value='none',
                    id='axes_criterion',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ], style={"marginBottom": "10px"}),
        ]),

        html.Br(),
        # Marker Size
        html.Div(children=[html.Label('Marker size: '),
                           dcc.Slider(marker_size_min, marker_size_max, step=None, id='marker_size', value=15,
                                      marks={i: str(i) for i in range(marker_size_min, marker_size_max + 1, 2)})]),
        html.Div(children=[html.Label('Line Thickness: '),
                           dcc.Slider(line_size_min, line_size_max, step=None, id='line_size', value=5,
                                      marks={i: str(i) for i in range(line_size_min, line_size_max + 1)})]),

        html.Br(),
        # coarse filter
        html.Label('Color:'),
        dcc.Dropdown(all_columns, id='color_column', multi=False, placeholder='Iterate color over ...'),
        dcc.Dropdown(all_columns_colored, id='color_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Label('Line style:'),
        dcc.Dropdown(all_columns, id='style_column', multi=False,
                     placeholder='Iterate line style over ...'),
        dcc.Dropdown(all_columns_styled, id='style_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Label('Marker symbol:'),
        dcc.Dropdown(all_columns, id='marker_column', multi=False, placeholder='Iterate marker symbols over ...'),
        dcc.Dropdown(all_columns_markered, id='marker_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Label('Row (subplot):'),
        dcc.Dropdown(all_columns, id='row_column', multi=False, placeholder='Iterate subplot rows over...'),
        dcc.Dropdown(row_iterator_filtered, id='row_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Label('Column (subplot):'),
        dcc.Dropdown(all_columns, id='column_column', multi=False, placeholder='Iterate subplot columns over...'),
        dcc.Dropdown(column_iterator_filtered, id='column_elements', multi=True, placeholder='Filter values'),
        html.Br(),
        html.Div(
            id="subplot-size",
            style={'display': 'none'},  # start hidden
            children=[
                html.Label("Width (px):"),
                dcc.Input(
                    id="subplot-width",
                    type="number",
                    min=200, max=2000,
                    value=900,
                ),
                '\t\t',
                html.Label("Height (px):"),
                dcc.Input(
                    id="subplot-height",
                    type="number",
                    min=200, max=2000,
                    value=800,
                ),
            ]
        ),

        html.Hr(),
        html.Br(),
        html.Div([
            html.Label('Normalization:', style={'marginRight': '10px'}),
            dcc.RadioItems(
                options=['ON', 'OFF'],
                value='OFF',
                id='ref_mode',
                labelStyle={'display': 'inline-block', 'marginRight': '10px'}
            )
        ], style={"display": "flex", "alignItems": "center"}),

        html.Label('Normalization selection:'),
        dcc.RadioItems(norm_el, id='plot_type'),

    ], style={'display': 'inline-block', "margin-left" : "10px", "width":"24%"}),

    # subframe right side for filter selection (optional)
    html.Div(
        className='plot window',
        children=[
            dcc.Graph(className='right_content', id='example-graph', style={'height': '100%'}, figure=go.Figure()),
    ],style={'display': 'inline-block', "width":"80%"}),

    dcc.Store(id="last-fig"),
    dcc.Store(id="last-csv"),

], style={'font-family': 'sans-serif'})

########################################################################################################################
### definition of callbacks - this asigns actions to buttons, radios, sliders, ...
########################################################################################################################
'''
 @app.callback is a decorator used to define interactivity between components in your app.
 It connects inputs (like dropdowns, sliders, buttons) 
 to outputs (like graphs, tables, or text), 
 so that when a user interacts with the input, the output updates automatically.
 
 Key Concepts
 Input: What triggers the update (e.g., a change in a dropdown or slider).
 Output: What you want to update (e.g., the figure of a graph or the children of a Div).
 State: Optional. Like Input, but it doesn’t trigger the callback—it's just extra data passed in.
 '''


### Callback Funktion for writing settings.json file
@app.callback(
    dash.dependencies.Output('download-settings-json', 'data'),

    dash.dependencies.Input('download-settings-button', 'n_clicks'),
    dash.dependencies.State('download-name', 'value'),

    dash.dependencies.State('y_tags1', 'value'),
    dash.dependencies.State('y_tags2', 'value'),
    dash.dependencies.State('x_tag', 'value'),
    dash.dependencies.State('filter_column', 'value'),
    dash.dependencies.State('filter_elements', 'value'),
    dash.dependencies.State('color_column', 'value'),
    dash.dependencies.State('color_elements', 'value'),
    dash.dependencies.State('style_column', 'value'),
    dash.dependencies.State('style_elements', 'value'),
    dash.dependencies.State('marker_column', 'value'),
    dash.dependencies.State('marker_elements', 'value'),
    dash.dependencies.State('plot_type', 'value'),
    dash.dependencies.State('line_mode', 'value'),
    dash.dependencies.State('ref_mode', 'value'),
    dash.dependencies.State('iter_criterion', 'value'),
    dash.dependencies.State('axes_criterion', 'value'),
    dash.dependencies.State('marker_size', 'value'),
    dash.dependencies.State('line_size', 'value'),
    dash.dependencies.State('row_column', 'value'),
    dash.dependencies.State('row_elements', 'value'),
    dash.dependencies.State('column_column', 'value'),
    dash.dependencies.State('column_elements', 'value'),
    dash.dependencies.State('colormap_column', 'value'),
    dash.dependencies.State('colormap_elements', 'value'),
    prevent_initial_call=True
)
def output_settings_json(
        n_clicks,
        filename,
        y_tags1,
        y_tags2,
        xTag,
        coarse_in,
        fine_in,
        color_column,
        color_elements,
        style_column,
        style_elements,
        marker_column,
        marker_elements,
        plot_type,
        line_mode,
        ref_mode,
        yTag_criterion,
        yaxes_criterion,
        markerSize,
        lineSize,
        row_column,
        row_elements,
        column_column,
        column_elements,
        colormap_column,
        colormap_elements
):

    if filename == '':
        filename = 'exported_settings.json'
    if '.json' not in filename:
        filename = filename + '.json'
    settings_dict = {
        'yTags1': y_tags1,
        'yTags2': y_tags2,
        'xTag': xTag,
        'coarse_in': coarse_in,
        'fine_in': fine_in,
        'color_column': color_column,
        'color_elements': color_elements,
        'style_column': style_column,
        'style_elements': style_elements,
        'marker_column': marker_column,
        'marker_elements': marker_elements,
        'plot_type': plot_type,
        'line_mode': line_mode,
        'ref_mode': ref_mode,
        'yTag_criterion': yTag_criterion,
        'yaxes_criterion': yaxes_criterion,
        'markerSize': markerSize,
        'lineSize': lineSize,
        'row_column' : row_column,
        'row_elements' : row_elements,
        'column_column' : column_column,
        'column_elements' : column_elements,
        'colormap_column' : colormap_column,
        'colormap_elements' : colormap_elements
    }
    return dict(content=json.dumps(settings_dict, indent=4), filename=filename)

### Callback Funktion for reading settings.json file
@app.callback(
    dash.dependencies.Output('settings-file', 'data'),

    dash.dependencies.Input('upload-setting-file', 'contents'),
    prevent_initial_call=True
)
def upload_setting_file(contents):
    if contents is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        settings = json.loads(decoded)
        return settings
    else:
        return dash.no_update


### Callback Funktion for reading data from csv files into the app data storage
@app.callback(
    ### output = what is updated with function return
    # returns dict (df.to_dict('records')) of csv data to browser store
    dash.dependencies.Output('data', 'data'),
    # returns string of file names to uploaded files window
    dash.dependencies.Output('uploaded-files', 'value'),
    # returns list of file names to browser store
    dash.dependencies.Output('file-names', 'data'),

    ### intput = triggers
    # when new files in drag&drop
    dash.dependencies.Input('upload-data', 'contents'),
    # when reset-data button pressed
    dash.dependencies.Input('reset-data', 'n_clicks'),

    ### state = input data where changes do not immediately trigger
    dash.dependencies.State('upload-data', 'filename'),
    # old files are input to append the newly added files
    dash.dependencies.State('data', 'data'),
    dash.dependencies.State('file-names', 'data'),

    prevent_initial_call=True
)
def update_upload(new_contents, n_clicks, new_filenames,data, file_names, ):
    """
    This function loads the data from provided csv-files in the Drag and Drop field to the plot app.
    This data can then be plotted.
    Old files are kept until 'reset-data' button is triggered.
    Added files are checked to prevent a doubling of files in the app

    :param new_contents: file?data? from Drag&Drop window
    :param new_filenames: filenames of files from Drag&Drop
    #:param list_of_dates: dates of files from Drag&Drop
    :param old_list: takes previously read files as input to append new files from drag
    :param n_clicks: changes when reset button is triggered
    :return: list with names, data and dates of all files in app in case additional data is loaded later
    """
    data = pd.DataFrame(data)
    ctx = dash.callback_context

    # if data reset button is triggered, the data is reset and an empty list returned
    if ctx.triggered_id == 'reset-data':
        return pd.DataFrame().to_dict('records'), 'No Files uploaded', list()

    # when files are uploaded, they are sorted (together with old files)
    file_names.extend(new_filenames)

    # all files are read into df for better handling/plotting
    print('Start reading')
    children = [parse_contents(c, n) for c, n in zip(new_contents, new_filenames)]

    # add new data to existing
    print('Finish reading\nStart concating')
    data = pd.concat([data]+[iter for iter in children], ignore_index=True)
    return_dict = data.to_dict('records')

    print('Returning Data')
    return return_dict, '\n'.join(file_names), file_names

def selector(data, column, selections):
    if column and selections:
        iterator = {'tag': column, 'restrict': selections}
        elements = data.loc[:, iterator['tag']].sort_values().unique()
        values = iterator['restrict']
    else:
        if column and column in data.columns:
            iterator = {'tag': column}
            elements = data.loc[:, iterator['tag']].sort_values().unique().tolist()
        else:
            iterator = {'tag': 'all'}
            elements = list()
        values = ['all']
    return iterator, values, elements

@app.callback(

    dash.dependencies.Output('y_tags1', 'options'),
    dash.dependencies.Output('y_tags2', 'options'),
    dash.dependencies.Output('x_tag', 'options'),
    dash.dependencies.Output('filter_column', 'options'),
    dash.dependencies.Output('filter_elements', 'options'),
    dash.dependencies.Output('color_column', 'options'),
    dash.dependencies.Output('color_elements', 'options'),
    dash.dependencies.Output('style_column', 'options'),
    dash.dependencies.Output('style_elements', 'options'),
    dash.dependencies.Output('marker_column', 'options'),
    dash.dependencies.Output('marker_elements', 'options'),
    dash.dependencies.Output('row_column', 'options'),
    dash.dependencies.Output('row_elements', 'options'),
    dash.dependencies.Output('column_column', 'options'),
    dash.dependencies.Output('column_elements', 'options'),
    dash.dependencies.Output('colormap_column', 'options'),
    dash.dependencies.Output('colormap_elements', 'options'),

    dash.dependencies.Output('y_tags1', 'value'),
    dash.dependencies.Output('y_tags2', 'value'),
    dash.dependencies.Output('x_tag', 'value'),
    dash.dependencies.Output('filter_column', 'value'),
    dash.dependencies.Output('filter_elements', 'value'),
    dash.dependencies.Output('color_column', 'value'),
    dash.dependencies.Output('color_elements', 'value'),
    dash.dependencies.Output('style_column', 'value'),
    dash.dependencies.Output('style_elements', 'value'),
    dash.dependencies.Output('marker_column', 'value'),
    dash.dependencies.Output('marker_elements', 'value'),
    dash.dependencies.Output('row_column', 'value'),
    dash.dependencies.Output('row_elements', 'value'),
    dash.dependencies.Output('column_column', 'value'),
    dash.dependencies.Output('column_elements', 'value'),
    dash.dependencies.Output('colormap_column', 'value'),
    dash.dependencies.Output('colormap_elements', 'value'),

    dash.dependencies.Input('data', 'data'),
    dash.dependencies.Input('y_tags1', 'value'),
    dash.dependencies.Input('y_tags2', 'value'),
    dash.dependencies.Input('x_tag', 'value'),
    dash.dependencies.Input('filter_column', 'value'),
    dash.dependencies.Input('filter_elements', 'value'),
    dash.dependencies.Input('color_column', 'value'),
    dash.dependencies.Input('color_elements', 'value'),
    dash.dependencies.Input('style_column', 'value'),
    dash.dependencies.Input('style_elements', 'value'),
    dash.dependencies.Input('marker_column', 'value'),
    dash.dependencies.Input('marker_elements', 'value'),
    dash.dependencies.Input('row_column', 'value'),
    dash.dependencies.Input('row_elements', 'value'),
    dash.dependencies.Input('column_column', 'value'),
    dash.dependencies.Input('column_elements', 'value'),
    dash.dependencies.Input('colormap_column', 'value'),
    dash.dependencies.Input('colormap_elements', 'value'),
    dash.dependencies.Input('settings-file', 'data'),
    prevent_initial_call=True,
)
def populate_dropdowns(
        data_to_process,
        y_tags1,
        y_tags2,
        x_tag,
        filter_column,
        filter_elements,
        color_column,
        color_elements,
        style_column,
        style_elements,
        marker_column,
        marker_elements,
        row_column,
        row_elements,
        column_column,
        column_elements,
        colormap_column,
        colormap_elements,
        settings
):

    data_to_process = pd.DataFrame(data_to_process)
    ctx = dash.callback_context

    print('start populating dropdowns, because of ' + str(ctx.triggered_id))

    if ctx.triggered_id == 'reset-data':
        print('should never happen !?')
        return [list(), list(), list(), list(), list(), list(), list(), list(), list(), list(), list(), list(),
                list(), list(), list(), list(), list(), list(), list(), list(), list(), list(), list(), list(),
                list(), list(), list(), list(), list(), list(), list(), list(), list()]

    if ctx.triggered_id == 'settings-file':
        print('triggered from settings file')
        y_tags1 = settings['yTags1']
        y_tags2 = settings['yTags2']
        x_tag = settings['xTag']
        filter_column = settings['coarse_in']
        filter_elements = settings['fine_in']
        color_column = settings['color_column']
        color_elements = settings['color_elements']
        style_column = settings['style_column']
        style_elements = settings['style_elements']
        marker_column = settings['marker_column']
        marker_elements = settings['marker_elements']
        column_column = settings['column_column']
        column_elements = settings['column_elements']
        row_column = settings['row_column']
        row_elements = settings['row_elements']
        colormap_column = settings['colormap_column']
        colormap_elements = settings['colormap_elements']

    all_columns = data_to_process.columns.values

    color_iterator, colorVals, clr_elmnts = selector(data_to_process, color_column, color_elements)
    style_iterator, styleVals, style_elmnts = selector(data_to_process, style_column, style_elements)
    marker_iterator, markerVals, marker_elmnts = selector(data_to_process, marker_column, marker_elements)
    row_iterator, rowVals, row_elmnts = selector(data_to_process, row_column, row_elements)
    column_iterator, columnVals, column_elmnts = selector(data_to_process, column_column, column_elements)
    filter_iterator, filterVals, filter_elmnts = selector(data_to_process, filter_column, filter_elements)
    colormap_iterator, colormapVals, colormap_elmnts = selector(data_to_process, colormap_column, colormap_elements)

    print('finish populating dropdowns')

    return [all_columns, all_columns, all_columns, all_columns, filter_elmnts, all_columns,
            clr_elmnts, all_columns, style_elmnts, all_columns, marker_elmnts, all_columns, row_elmnts, all_columns,
            column_elmnts, all_columns, colormap_elmnts, y_tags1, y_tags2, x_tag, filter_column, filter_elements, color_column,
            color_elements, style_column, style_elements,marker_column, marker_elements, row_column, row_elmnts,
            column_column, column_elements, colormap_column, colormap_elements]

@app.callback(
    ### output = what is updated with function return
    dash.dependencies.Output('example-graph', 'figure'),
    dash.dependencies.Output('ref_mode', 'value'),
    dash.dependencies.Output('plot_type', 'options'),
    dash.dependencies.Output('download-dataframe-csv', 'data'),
    dash.dependencies.Output('download-plot-html', 'data'),
    dash.dependencies.Output('subplot-size', 'style'),
    dash.dependencies.Output('last-fig', 'data'),
    dash.dependencies.Output('last-csv', 'data'),

    ### input - what triggers function when data changes
    dash.dependencies.Input("update-plot", "n_clicks"),
    dash.dependencies.Input('data', 'data'),
    dash.dependencies.Input('y_tags1', 'value'),
    dash.dependencies.Input('y_tags2', 'value'),
    dash.dependencies.Input('x_tag', 'value'),
    dash.dependencies.Input('ref_mode', 'value'),
    dash.dependencies.Input('plot_type', 'value'),
    dash.dependencies.Input('line_mode', 'value'),
    dash.dependencies.Input('filter_column', 'value'),
    dash.dependencies.Input('filter_elements', 'value'),
    dash.dependencies.Input('color_column', 'value'),
    dash.dependencies.Input('color_elements', 'value'),
    dash.dependencies.Input('style_column', 'value'),
    dash.dependencies.Input('style_elements', 'value'),
    dash.dependencies.Input('marker_column', 'value'),
    dash.dependencies.Input('marker_elements', 'value'),
    dash.dependencies.Input('reset-data', 'n_clicks'),
    dash.dependencies.State('download-name', 'value'),
    dash.dependencies.Input('download-button-csv', 'n_clicks'),
    dash.dependencies.Input('download-button-html', 'n_clicks'),
    dash.dependencies.Input('iter_criterion', 'value'),
    dash.dependencies.Input('axes_criterion', 'value'),
    dash.dependencies.Input('marker_size', 'value'),
    dash.dependencies.Input('line_size', 'value'),
    dash.dependencies.Input('settings-file', 'data'),
    dash.dependencies.Input('row_column', 'value'),
    dash.dependencies.Input('row_elements', 'value'),
    dash.dependencies.Input('column_column', 'value'),
    dash.dependencies.Input('column_elements', 'value'),
    dash.dependencies.Input('colormap_column', 'value'),
    dash.dependencies.Input('colormap_elements', 'value'),
    dash.dependencies.Input('subplot-width', 'value'),
    dash.dependencies.Input('subplot-height', 'value'),
    dash.dependencies.Input('last-fig', 'data'),
    dash.dependencies.Input('last-csv', 'data'),
    prevent_initial_call=True,
)
def update_output(
        n_clicks_update,
        data_to_process,
        y_tags1,
        y_tags2,
        x_tag,
        normalization_mode,
        plot_type,
        line_mode,
        filter_column,
        filter_elements,
        color_column,
        color_elements,
        style_column,
        style_elements,
        marker_column,
        marker_elements,
        n_clicks2,
        filename,
        n_clicks_download_csv,
        n_clicks_download_html,
        y_tag_criterion,
        y_axis_criterion,
        marker_size,
        line_size,
        settings,
        row_column,
        row_elements,
        column_column,
        column_elements,
        colormap_column,
        colormap_elements,
        fig_w,
        fig_h,
        last_fig,
        last_csv,
):
    '''
    Function to plot values from the provided .csv frames
    Graphic is updated on every change of an input parameter

    :param yTags: columns plotted on yAxis for x-values from xTag (multi-select)
    :param x_tag: column that gives x-values (single-select)
    :param normalization_mode: state button, normalization on or off
    :param plot_type: yTag to use as reference basis
    :param line_mode: box for line mode (points with lines or only points)
    :param coarse_in: filter column (for which column yTags are filtered), (single-select)
    :param fine_in: values from filter column for which data is displayed (multi-select)
    :param color_column: different plot colours based on different entries from this column (single-select)
    :param color_elements: additional filtering possibility (similar to fine_in), (multi-select)
    :param style_column: different line styles (-,--,.) based on different entries from this column (single-select)
    :param style_elements: additional filtering possibility (similar to fine_in), (multi-select)
    :param marker_column: different marker styles based on different entries from this column (single-select)
    :param marker_elements: additional filtering possibility (similar to fine_in), (multi-select)
    :param n_clicks: refreshes the figure, especially needed when new data is uploaded
    :param n_clicks2: erases the plot, when input data is reset
    :return: a lot...
    '''
    print('start update output')
    ctx = dash.callback_context
    buttons = {"update-plot", "reset-data", "download-button-csv", "download-button-html"}

    if ctx.triggered_id in buttons:
        print('updateing because of' +str(ctx.triggered_id))

        print('Converting json to pandas')
        data_to_process = pd.DataFrame(data_to_process)

        print('A')
        if last_fig:
            fig = plotly.io.from_json(last_fig)
        else:
            fig = make_subplots(rows=1, cols=1, shared_xaxes=True, shared_yaxes=True)

        print('B')
        fig_json = last_fig
        complete_csv_json = last_csv
        download_command_csv = None
        download_command_html = None
        normalization_values = ["OFF", list()]

        print('C')
        if ctx.triggered_id == 'reset-data':
            # reset plot
            fig = make_subplots(
                    rows=1, cols=1,
                    shared_xaxes=True, shared_yaxes=True,
            )
            return [fig, *normalization_values, None, None, {'display': 'none'}, None, None]
            print('D')
        elif ctx.triggered_id == 'download-button-csv':
            if filename == '':
                filename = 'exported_plot_data.csv'
            if '.csv' not in filename:
                filename = filename + '.csv'
            nan_value = float('NaN')
            output_df = pd.read_json(last_csv, orient="split")

            if not output_df.empty:
                output_df.replace('', nan_value, inplace=True)
                output_df.dropna(how='all', axis=1, inplace=True)
            download_command_csv = dcc.send_data_frame(output_df.to_csv, filename)


            print('E')
        elif ctx.triggered_id == 'download-button-html':
            if filename == '':
                filename = 'exported_plot_data.html'
            if '.html' not in filename:
                filename += '.html'

            figPath = os.path.join(os.path.dirname(data_to_process[0]), filename) if isinstance(data_to_process, list) else filename
            fig.write_html(figPath)
            download_command_html = dcc.send_file(figPath)
            print('F')
        # UPDATE PLOT   # TODO should be a callback, if upload settings, dropdowns are not updated
        if ctx.triggered_id == 'settings-file':
            print('G')
            plot_type = settings['plot_type']
            line_mode = settings['line_mode']
            normalization_mode = settings['ref_mode']
            y_tag_criterion = settings['yTag_criterion']
            y_axis_criterion = settings['yaxes_criterion']
            marker_size = settings['markerSize']
            line_size = settings['lineSize']

        print('H')
        color_iterator, _, _ = selector(data_to_process, color_column, color_elements)
        style_iterator,  _, _ = selector(data_to_process, style_column, style_elements)
        marker_iterator,  _, _ = selector(data_to_process, marker_column, marker_elements)
        row_iterator,  _, _ = selector(data_to_process, row_column, row_elements)
        column_iterator,  _, _ = selector(data_to_process, column_column, column_elements)
        filter_iterator,  _, _ = selector(data_to_process, filter_column, filter_elements)
        colormap_iterator, _, _ = selector(data_to_process, colormap_column, colormap_elements)

        print('I')
        if column_iterator['tag'] != 'all' or column_iterator['tag'] != 'all':
            subplot_size = {'display': 'block'}
        else:
            subplot_size = {'display': 'none'}
            fig_w, fig_h = None, None

        print('J')
        if ctx.triggered_id == "update-plot":
            print('Starting Update')
            fig, complete_csv, normalization_values = PlotIterator.PlotIterator(
                data_to_process=data_to_process,
                xTag=x_tag,
                y_tags1=y_tags1,
                y_tags2=y_tags2,
                ref_mode=normalization_mode,
                plot_type=plot_type,
                line_mode=line_mode,
                color_iterator=color_iterator,
                style_iterator=style_iterator,
                marker_iterator=marker_iterator,
                filter_iterator=filter_iterator,
                colormap_iterator=colormap_iterator,
                n_clicks2=n_clicks2,
                filename=filename,
                yTag_criterion=y_tag_criterion,
                yaxes_criterion=y_axis_criterion,
                markerSize=marker_size,
                lineSize=line_size,
                row_iterator=row_iterator,
                column_iterator=column_iterator,
                fig_w=fig_w,
                fig_h=fig_h,
            )
            print('Figure Created')
            fig_json = fig.to_json()
            complete_csv_json = pd.DataFrame(complete_csv).to_json(date_format="iso", orient="split")
            normalization_mode = "OFF"
            print('Returning Figure')

        print('finish update output')
        return [
            fig,
            normalization_mode,
            normalization_values,
            download_command_csv,
            download_command_html,
            subplot_size,
            fig_json,
            complete_csv_json,
        ]

    else:
        print('unintended update')
        # why is not every input (except buttons) converted to state
        raise dash.exceptions.PreventUpdate

def parse_contents(contents, filename):#, date):
    '''
    This function is used in update_upload to read the data from .csv files to df

    :param contents: Content at filename
    :param filename: Filename to import
    :param date: Date of last change
    :return: single DataFrame specified in :param filename from :param contents
    '''
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            print('Filetype not supported. Please upload .csv or .xls files.')
        # insert all column and filename column for plotting/data identification
        if 'Unnamed: 0' in df:
            df.drop(columns=['Unnamed: 0'], inplace=True)
        try:
            df.insert(0, 'all', 'all')
        except ValueError:
            pass
        try:
            df.insert(0, 'filename', os.path.splitext(filename)[0])
        except ValueError:
            pass

    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return df

def check_port_availability(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except socket.error as e:
            return False


### Callback Funktion for updating ixent logo
@app.callback(
    dash.dependencies.Output('logo', 'src'),
    dash.dependencies.Input('confirm', 'submit_n_clicks_timestamp'),
    dash.dependencies.Input('confirm', 'cancel_n_clicks_timestamp'),
    prevent_initial_call=True)
def update_logo(submit_timestamp, cancel_timestamp):
    if not cancel_timestamp:
        cancel_timestamp = -1
    if not submit_timestamp:
        submit_timestamp = -1
    if submit_timestamp > cancel_timestamp:
        return app.get_asset_url('gnp.bin')
    else:
        return app.get_asset_url('ixent_logo_400.png')

dash_host = '0.0.0.0'
dash_port = 8050
debug = False

# find available port if 8050 is blocked
while not check_port_availability(dash_host, dash_port):
    dash_port += 1
if __name__ == "__main__":
    app.run(debug=True)

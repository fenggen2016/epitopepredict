#!/usr/bin/env python

"""
    epitopepredict, methods for supporting web app
    Created Sep 2017
    Copyright (C) Damien Farrell
"""

from __future__ import absolute_import, print_function
import sys,os,glob
import pandas as pd
import numpy as np
from . import base, plotting, sequtils, analysis
from bokeh.models import ColumnDataSource, Slider
from bokeh.models.widgets import DataTable, TableColumn, Select, Button, Slider, TextInput
from bokeh.layouts import row, column, gridplot, widgetbox, layout
from bokeh.embed import components

path = 'results'
predictors = base.predictors
plotkinds = ['tracks','bar','text']

def get_file_lists(path):

    names = []
    for p in predictors:
        files = glob.glob(os.path.join(path, p, '*.csv'))
        n = [os.path.splitext(os.path.basename(i))[0] for i in files]
        names.extend(n)
    names = set(names)
    names = sorted(names)
    return names

def get_results(path, predictor, name=None):

    P = base.get_predictor(predictor)
    if name is not None:
        filename = os.path.join(path, predictor, name)
        P.load(filename+'.csv')
    else:
        P.load(path=os.path.join(path, predictor))
    #print filename
    #print P.data
    return P

def get_results_info(P):
    """Info on sequence used for prediction"""

    df = P.data
    if df is None:
        return ''
    #l = base.get_length(df)
    seq = sequence_from_peptides(P.data)
    l = len(seq)
    return {'length':l}

def sequence_from_peptides(df):
    """Derive sequence from set of peptides"""

    l = base.get_length(df)
    df = df.drop_duplicates('pos').sort_values('pos')
    x = df.peptide.str[0]
    last = df.iloc[-1].peptide[1:]
    x = ''.join(x)
    x = x + last
    return x

def get_alleles(preds):
    """get available alleles"""

    a = []
    for P in preds:
        df = P.data
        if df is None:
            continue
        x = df.allele.unique()
        a.extend(x)
    a = list(set(a))
    return a

def get_predictors(path, name=None):
    """Get a set of predictors with available results"""

    preds = []
    for pred in predictors:
        P = get_results(path, pred, name)
        if P.data is not None and len(P.data)>0:
            preds.append(P)
    return preds

def get_sequences(pred):
    """Get set of sequences from loaded data"""

    seqs = {}
    df = pred.data
    for n,df in pred.data.groupby('name'):
        s = sequence_from_peptides(df)
        seqs[n] = s
    seqs = pd.DataFrame(seqs.items(), columns=['name','seq'])
    #print (seqs)
    return seqs

def sequences_to_html_table(seqs, classes=''):
    """Convert seqs to html"""

    tabledata=[]
    tabledata.append('<th>name</th><th>sequence</th>')
    for i,row in seqs.iterrows():
        seq = row.seq
        name = row['name']
        seqhtml = ''
        for i in range(len(seq)):
            seqhtml += '<span style="background-color:white">%s</span>' %seq[i]
        row = '<tr><th>%s</th><td>%s</td></tr>' %(name, seqhtml)
        tabledata.append(row)
    table = '\n'.join(tabledata)
    table = '<table class="%s">\n' %classes + table + '</table>'
    return table

def create_sequence_html(preds, name='', classes='', **kwargs):

    seqs=[]
    tabledata=[]
    tabledata.append('<th>allele</th><th>sequence</th>')
    colors = plotting.get_bokeh_colors()

    for P in preds:
        df = P.data
        if df is None:
            continue
        b = P.getBinders(**kwargs)
        l = base.get_length(df)
        seq = sequence_from_peptides(df)
        clr = colors[P.name]
        grps = b.groupby('allele')
        for a,g in grps:
            pos=[]
            for i in g.pos: pos.extend(np.arange(i,i+l))
            seqhtml = ''
            for i in range(len(seq)):
                if i in pos:
                    seqhtml += '<span style="background-color:%s; opacity:0.8">%s</span>' %(clr,seq[i])
                else:
                    seqhtml += '<span style="background-color:white">%s</span>' %seq[i]
            row = '<tr><th>%s</th><td>%s</td></tr>' %(a, seqhtml)
            tabledata.append(row)
    table = '\n'.join(tabledata)
    table = '<table class="%s">\n' %classes + table + '</table>'
    return table

def sequence_to_html_grid(preds, classes='', **kwargs):
    """Put aligned or multiple identical rows in dataframe and convert to
    grid of aas as html table"""

    seqdf = []
    bdata = {}
    for P in preds:
        df = P.data
        if df is None:
            continue
        b = P.getBinders(**kwargs)
        bdata[P.name] = b
        #pb = P.promiscuousBinders(binders=b,**kwargs)
        l = base.get_length(df)
        grps = b.groupby('allele')
        alleles = grps.groups
        seq = sequence_from_peptides(df)
        #put into new df one row per allele
        x = [(P.name,a,seq) for a in alleles]
        df = pd.DataFrame(x, columns=['pred','allele','seq']).set_index(['pred','allele'])
        df = df.seq.apply(lambda x: pd.Series(list(x)))
        seqdf.append(df)
    seqdf = pd.concat(seqdf)

    colors = plotting.get_bokeh_colors()

    def color(x):
        p, a = x.name
        pos = []
        clr = colors[p]
        b = bdata[p]
        f = list(b[b.allele==a].pos)
        for i in f: pos.extend(np.arange(i,i+l))
        clrs = ['' for i in x]
        for i in pos:
            clrs[i] = 'background-color: %s; opacity: .8;' %clr
        return clrs

    s = seqdf.style\
             .set_table_attributes('class="%s"' %classes)\
             .apply(color,1)
    table = s.render()
    return table

def create_figures(preds, name='', kind='tracks', cutoff=5, n=2,
                   cutoff_method='default', **kwargs):
    """Get plots of binders for single protein/sequence"""

    figures = []
    if kind == 'tracks':
        plot = plotting.bokeh_plot_tracks(preds, title=name, width=700,
                         palette='Set1', cutoff=float(cutoff), n=int(n),
                         cutoff_method=cutoff_method)
        if plot is not None:
            figures.append(plot)
    elif kind == 'bar':
        alleles = get_alleles(preds)
        xr=None
        for a in alleles:
            plot = plotting.bokeh_plot_bar(preds, title=a, allele=a, width=None, x_range=xr )
            if xr==None:
                xr = plot.x_range
            figures.append(plot)
    return figures

def create_bokeh_table(path, name):
    """Create table of prediction data"""

    P = get_results(path, 'tepitope', name)
    if P.data is None:
        return
    df = P.data[:10]
    data = dict(
        peptide=df.peptide.values,
        pos=df.pos.values,
        score=df.score.values,
        allele=df.allele.values
    )
    #print (df)
    source = ColumnDataSource(data)
    columns = [
            TableColumn(field="peptide", title="peptide"),
            TableColumn(field="pos", title="pos"),
            TableColumn(field="score", title="score"),
            TableColumn(field="allele", title="allele"),
        ]
    table = DataTable(source=source, columns=columns, width=400, height=280)
    return table

def get_binder_tables(preds, name=None, view='binders', **kwargs):
    """Create html tables of prediction data from predictor objects. The
       data is assumed to be loaded into the predictors.
       Returns: dict of dataframes
       """

    data = {}
    drop=True
    import pylab as plt
    for P in preds:
        df = P.getBinders(name=name, **kwargs)
        if df is None:
            continue
        if view == 'promiscuous':
            df = P.promiscuousBinders(df, **kwargs)
        elif view == 'by allele':
            df = pd.pivot_table(P.data, index=['pos','peptide'],
                                columns='allele', values=P.scorekey)
            drop=False
        df = df.reset_index(drop=drop)
        data[P.name] = df
    return data

def dataframes_to_html(data, classes=''):

    tables = {}
    for k in data:
        df = data[k]
        s = df.style\
              .set_table_attributes('class="%s"' %classes)
              #.background_gradient(subset=[P.scorekey], cmap=cm) #%classes
        tables[k] = s.render(index=False)
    return tables

def dict_to_html(data):

    s = ''
    for k in data:
        s += '<a>%s: %s</a><br>' %(k,data[k])
    return s

def column_to_url(df, field, path):
    """Add urls to specified field in a dataframe by prepending the supplied
       path."""

    if len(df) == 0:
        return df
    df[field] = df.apply(lambda x:
                '<a href=%s>%s</a>' %(path+x[field],x[field]),1)
    return df

def tabbed_html(items):
    """Create html for a set of tabbed divs from dict of html code, one for
       each tab. Uses css classes defined in static/custom.css"""

    name = 'tab-group'
    html = '<div class="tabs">\n'
    for t in items:
        html += '<div class="tab">\n'
        html += '<input type="radio" id="%s" name="%s" checked>\n' %(t,name)
        html +=	'<label for="%s">%s</label>\n' %(t,t)
        html +=	'<div class="content">\n'
        html += items[t]
        #html += '<p>%s</p>' %t
        html +=	'</div></div>\n'
    html += '</div>'
    #print (html)
    return html

def create_widgets():

    select = Select(title="Name:", value="name", options=["foo", "bar"])
    slider = Slider(start=0, end=100, value=5, step=.5, title="Cutoff")
    button = Button(label="Submit", button_type="success")
    #text_input = TextInput(value="default", title="Name:")
    return widgetbox([button,select,slider], width=200)

def test():
    from bokeh.io import output_file, show
    path = 'results'
    name = 'Rv0011c'
    kwargs ={'cutoff_method':'default'}
    preds = get_predictors(path, name)
    plots = create_figures(preds)
    #table = create_bokeh_table(path, name)
    tables = create_binder_tables(preds, name)
    grid = gridplot(plots, ncols=1, merge_tools=True)
    widgets = create_widgets()
    l = layout([[ plots, widgets ]], ncols=2, nrows=1)
    #script, div = components(l)
    show(l)

if __name__ == "__main__":
    test()
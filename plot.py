#!/usr/bin/python

try: import simplejson as json
except ImportError: import json
import sys
import os
import os.path

# writes data output file as basename.dat from the given data, with 'dirs' as
# column headers.
def write_data_file(basename, data, dirs):

    f = open(basename + '.dat', 'w')

    for row in data:
        f.write('"%s" ' % row[0].replace('_', '-'))
        f.write(' '.join(map(lambda x: str(x), row[1:])))
        f.write("\n")

    f.close()

def avg(l):
    return sum(l) / len(l) if len(l) > 0 else 0.0
def geomean(l):
    return math.pow(reduce(lambda x,y:x*y, l), 1.0 / len(l)) if len(l) > 0 else 0.0

def apply_to_columns(data, column_func):
    def transpose(ll):
        if len(ll) == 0: return []
        cols = [ [] for i in range(len(ll[0]) - 1) ]
        for row in ll:
            for i in range(1, len(row)):
                cols[i-1].append(row[i])
        return cols
    
    t = transpose(data)
    return map(column_func, t)

def add_avg(data, mean=False, geomean=False):

    if len(data) == 0: return []

    blankrow = [''] + [0.0 for i in range(len(data[0]))]

    if mean:
        avg_bars = apply_to_columns(data, avg)
        data.append(blankrow)
        data.append(['AVG'] + avg_bars)
    if geomean:
        avg_bars = apply_to_columns(data, geomean)
        data.append(blankrow)
        data.append(['GEOMEAN'] + avg_bars)

    return data

def max_y(data):
    return max(apply_to_columns(data, max))

def bar_colors(n):
    if n == 0: return []
    if n == 1: return ['#000000']
    if n == 2: return ['#444444', '#cccccc']
    if n == 3: return ['#444444', '#888888', '#cccccc']
    if n == 4: return ['#333333', '#666666', '#999999', '#cccccc']
    if n > 4: return ( (n+3)/4 * bar_colors(4) ) [0:n]

# writes gnuplot file for a grouped bargraph of the data.
def write_gnuplot_file(basename, dirs, stat, title):

    f = open(basename + '.gnuplot', 'w')

    f.write("""
set term postscript eps enhanced "Times-Roman,14"
set output "%s.eps"
set style fill pattern border lc rgbcolor "black"
set datafile missing '-'
set style data histogram
set autoscale x
set grid ytics
set key top right
set xtic rotate by -90 nomirror
set title "%s"
set ylabel "%s"
""" % (basename, title.replace('_', '-'), stat.replace('_', '-')))

    colors = bar_colors(len(dirs))

    f.write("plot ")
    i = -1
    for d in dirs:
        i += 1
        if i > 0: f.write(", ")
        f.write("\"%s.dat\" u %d" % (basename, i+2))
        if i == 0: f.write(":xtic(1)")
        f.write(" ti \"%s\" fill solid lc rgbcolor \"%s\" lt -1 lw 0.5" % (os.path.basename(d).replace('_', '-'), colors[i]))

    f.close()

def plot(basename):
    os.system("gnuplot %s.gnuplot" % basename)

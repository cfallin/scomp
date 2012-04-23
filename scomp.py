#!/usr/bin/env python

import model
import sys
try: import simplejson as json
except ImportError: import json

def usage():
    sys.stderr.write("""
    Usage: scomp -var VAR=VALUE -var VAR=VALUE model1.scomp [data_dir/ sheet_dir/ plot_dir/] model2.scomp ...

Each scompfile can be specified with a data, sheet, and plot directory, or
these can be omitted (and default to 'data/', 'sheets/' and 'plots/'
respectively).  If more than one scompfile is specified, data, sheet and plot
directories must be given explicitly.

""")

def main(args):
    if len(args) < 1:
        usage()
        sys.exit(1)

    varctx = {}
    while len(args) >= 2:
        if args[0] == '-var':
            varname, varval = map(lambda x: x.strip(), args[1].split('='))
            varctx[varname] = varval
            args = args[2:]
        else:
            break

    shortmode = False
    if len(args) == 1: shortmode = True
    num = 1 if shortmode else 3

    while len(args) >= num:
        if shortmode:
            fname = args[0]
            args = args[1:]
            datadir = 'data/'
            sheetdir = 'sheets/'
            plotdir = 'plots/'
        else:
            fname, datadir, sheetdir, plotdir = args[0:4]
            args = args[4:]

        m = model.model(varctx)

        o = json.load(open(fname))
        m.load(datadir, o)
        m.evaluate()
        m.output_sheets(sheetdir)
        m.output_plots(plotdir)

if __name__ == '__main__':
    main(sys.argv[1:])

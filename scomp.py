#!/usr/bin/env python

import model
import sys
import simplejson as json

def usage():
    sys.stderr.write("""
    Usage: scomp model1.scomp [data_dir/ sheet_dir/] model2.scomp ...

Each scompfile can be specified with a data and sheet directory, or
these can be omitted (and default to 'data/' and 'sheets/' respectively).
If more than one scompfile is specified, data and sheet directories must
be given explicitly.

""")

def main(args):
    if len(args) < 1:
        usage()
        sys.exit(1)

    shortmode = False
    if len(args) == 1: shortmode = True
    num = 1 if shortmode else 3

    while len(args) >= num:
        if shortmode:
            fname = args[0]
            args = args[1:]
            datadir = 'data/'
            sheetdir = 'sheets/'
        else:
            fname, datadir, sheetdir = args[0:3]
            args = args[3:]

        m = model.model()

        o = json.load(open(fname))
        m.load(datadir, o)
        m.evaluate()
        m.output_sheets(sheetdir)

if __name__ == '__main__':
    main(sys.argv[1:])

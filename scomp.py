#!/usr/bin/python

import model
import sys
import simplejson as json

def usage():
    sys.stderr.write("""
    Usage: scomp model1.scomp data_dir/ sheet_dir/ model2.scomp ...
""")

def main(args):
    if len(args) == 0:
        usage()
        sys.exit(1)

    while len(args) >= 3:
        fname, datadir, sheetdir = args[0:3]
        args = args[3:]

        m = model()

        try:
            o = json.load(open(fname))
        except:
            print "ERROR: Could not load model", fname
            sys.exit(1)

        try:
            m.load(datadir, o)
            m.evaluate()
        except:
            print "ERROR: Could not load/evaluate data"
            sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])

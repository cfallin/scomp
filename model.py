import re

import runs
import parser

# represents all state
class model:
    def __init__(self):

        # data loaded from dataset on disk
        self.configs = {} # indexed by short name

        # data given by user
        self.configlist = [] # order in list
        self.stats = [] # list of stats
        self.exprs = {}   # { config -> { colname -> expr } }
        self.exprlist = [] # gives ordering: list of colnames

        # data computed by evaluation
        self.grid = [] # array of row; row is array of ModelCell

        # output specs
        self.out_sheets = []
        self.out_plots = []

    def load(self, datadir, prog): # evaluate the given scomp program

        # first load specified configs
        self.configs = {}
        self.configlist = []

        for c in prog['configs']:
            longname = c[0]
            shortname = c[1]

            cfg = run.Config(datadir + '/' + longname)
            self.configs[shortname] = cfg
            self.configlist.append(shortname)
            self.exprs[c] = {}

        # save the list of stats
        self.stats = prog['stats']

        # read the list of exprs, matching and applying to appropriate configs
        self.exprlist = []
        for e in prog['exprs']:
            config_filter, statlist = e
            r = re.compile(config_filter.replace('*', '.*'))
            for c in self.configlist:
                if r.match(c):
                    for s in statlist:
                        name, expr = s
                        if not name in self.exprlist: self.exprlist.append(name)
                        self.exprs[c][name] = expr

        self.out_sheets = prog['sheets']
        self.out_plots = prog['plots']

        # parse and evaluate all exprs

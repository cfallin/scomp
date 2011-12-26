import re

import runs
from parser import Expr

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

        benchsets = []
        for c in prog['configs']:
            longname = c[0]
            shortname = c[1]

            cfg = run.Config(datadir + '/' + longname)
            self.configs[shortname] = cfg
            self.configlist.append(shortname)
            self.exprs[c] = {}
            benchsets.append(set(cfg.benches))

        # take union of all available benches
        self.benches = reduce(lambda x,y: x | y, benchsets)
        # also produce list of benches for which all results are present
        self.benches_all = reduce(lambda x,y: x & y, benchsets)

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
                        self.exprs[c][name] = Expr()
                        self.exprs[c][name].parse(expr, c)

        # parse exprs, construct dependences and worklist
        deps = {} # dict of lists
        affects = {} # dist of lists
        exprs = {} # list of Expr indexed by fullname
        vals = {} # current values
        for c in self.configlist:
            for name in self.exprs[c].keys():
                fullname = c + '.' + name
                worklist.add(fullname)
                exprs[fullname] = self.exprs[c][name]
                affects[fullname] = []
                deps[fullname] = self.exprs[c][name].deps
                vals[fullname] = None

        # get forward flow from backward flow
        for x in deps.keys():
            for source in deps[x]:
                if affects.has_key(source):
                    affects[source].append(x)
                    
        self.affects = affects

        self.out_sheets = prog['sheets']
        self.out_plots = prog['plots']

    # evaluates vals (stat and computed) for bench and returns dict
    # of values by fullname
    def evaluate_bench(self, bench):

        vals = {}

        # produce list of stat vals
        for c in self.configlist:
            for s in self.stats:
                if self.configs[c].runs.has_key(bench):
                    val = self.configs[c].runs[bench].stats[s]
                else:
                    val = 0.0
                vals[c + '.' + s] = val

        # produce list of all exprs
        worklist = set()
        for c in self.configlist:
            for name in self.exprs[c].keys():
                fullname = c + '.' + name
                worklist.add(fullname)

        # parse and evaluate all exprs
        while len(worklist) > 0:
            w = worklist.pop()
            e = exprs[w]
            oldval = vals[w]
            newval = e.evaluate(dict(vals.items() + statvals.items()))
            if newval != oldval:
                vals[w] = newval
                for dest in affects[w]:
                    worklist.add(dest)

        return vals

    # evaluates all benches, produces sheets
    def evaluate(self):
        vals = {}
        for bench in self.benches:


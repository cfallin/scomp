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
        statssets = []
        for c in prog['configs']:
            longname = c[0]
            shortname = c[1]

            cfg = runs.Config(datadir + '/' + longname)
            self.configs[shortname] = cfg
            self.configlist.append(shortname)
            self.exprs[shortname] = {}
            benchsets.append(set(cfg.benches))
            statssets.append(cfg.stats)

        # take union of all available benches
        self.benches = reduce(lambda x,y: x | y, benchsets)
        # also produce list of benches for which all results are present
        self.benches_all = reduce(lambda x,y: x & y, benchsets)

        stats_any = reduce(lambda x,y: x | y, statssets)
        stats_all = reduce(lambda x,y: x & y, statssets)

        # get the list of stats
        statsmatchers = []
        for x in prog['stats']:
            x = '^' + x.replace('*', '.*') + '$'
            r = re.compile(x)
            statsmatchers.append(r)

        self.stats = []
        for m in statsmatchers:
            matching = filter(lambda x: m.match(x), stats_any)
            for x in matching:
                if not x in self.stats:
                    self.stats.append(x)

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

        # parse exprs, construct dependences
        deps = {} # dict of lists
        affects = {} # dist of lists
        for c in self.configlist:
            for name in self.exprs[c].keys():
                fullname = c + '.' + name
                affects[fullname] = []
                deps[fullname] = self.exprs[c][name].deps

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
                if self.configs[c].runs.has_key(bench) and self.configs[c].runs[bench].stats.has_key(s):
                    st = self.configs[c].runs[bench].stats[s]
                    val = st.value()
                else:
                    val = 0.0
                vals[c + '.' + s] = val

        # produce list of all exprs
        worklist = set()
        exprs = {} # list of Expr indexed by fullname
        for c in self.configlist:
            for name in self.exprs[c].keys():
                fullname = c + '.' + name
                worklist.add(fullname)
                exprs[fullname] = self.exprs[c][name]
                vals[fullname] = 0.0

        # parse and evaluate all exprs
        while len(worklist) > 0:
            w = worklist.pop()
            e = exprs[w]
            if vals.has_key(w):
                oldval = vals[w]
            else:
                oldval = None
            #print "evaluate: bench", bench, "expr", w, "vals", vals
            newval = e.evaluate(vals)
            if newval != oldval:
                vals[w] = newval
                for dest in self.affects[w]:
                    worklist.add(dest)

        return vals

    # evaluates all benches, produces sheets
    def evaluate(self, sheetdir):
        vals = {}
        for bench in self.benches:
            vals[bench] = self.evaluate_bench(bench)

        for o in self.out_sheets:
            name, configlist = o[0], o[1]
            configs = []
            for c in configlist:
                if c == '*': configs.extend(self.configlist)
                else: configs.append(c)

            output = open(sheetdir + '/' + name + '.csv', 'w')

            output.write("Bench,Config," + ','.join(self.stats + self.exprlist) + "\n")

            b = list(self.benches)
            b.sort()
            for bench in b:
                for c in configs:
                    row = [bench, c]
                    for stat in self.stats + self.exprlist:
                        fullname = c + '.' + stat
                        if vals[bench].has_key(fullname):
                            val = vals[bench][fullname]
                        else:
                            val = None
                        if val == None: val = ''
                        row.append(str(val))
                    output.write(','.join(row) + "\n")
                output.write("\n")

            output.close()

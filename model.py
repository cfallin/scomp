import re
import os

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

        if prog.has_key('accept'):
            self.accept_rules = prog['accept']
        else:
            self.accept_rules = []

        benchsets = []
        statssets = []
        for c in prog['configs']:
            longname = c[0]
            shortname = c[1]

            l = []
            if longname.find('*') != -1:
                r = re.compile(longname.replace('*', '(.*)'))
                l = []
                for d in os.listdir(datadir):
                    if os.path.isdir(datadir + '/' + d):
                        m = r.match(d)
                        if m is None: continue
                        wildcard = m.groups()[0]
                        s = shortname.replace('$1', wildcard)
                        l.append( (d, s) )

            else:
                l = [ (longname, shortname) ]

            for p in l:
                cfg = runs.Config(datadir + '/' + p[0], self.accept_rules)
                self.configs[p[1]] = cfg
                self.configlist.append(p[1])
                self.exprs[p[1]] = {}
                benchsets.append(set(cfg.benches))
                statssets.append(cfg.stats)

        # take union of all available benches
        self.benches = reduce(lambda x,y: x | y, benchsets)
        # also produce list of benches for which all results are present
        self.benches_all = reduce(lambda x,y: x & y, benchsets)

        if prog.has_key('badbenches'):
            self.badbenches = prog['badbenches']
        else:
            self.badbenches = []

        if prog.has_key('benchmap'):
            self.benchmap = prog['benchmap']
        else:
            self.benchmap = {}
            for k in self.benches:
                self.benchmap[k] = k

        stats_any = reduce(lambda x,y: x | y, statssets)
        stats_all = reduce(lambda x,y: x & y, statssets)

        # get the list of stats
        statsmatchers = []
        if prog.has_key('stats'):
            for x in prog['stats']:
                x = '^' + x.replace('*', '.*') + '$'
                r = re.compile(x)
                statsmatchers.append(r)
        else:
            statsmatchers.append(re.compile('^.*$'))

        self.stats = []
        for m in statsmatchers:
            matching = filter(lambda x: m.match(x), stats_any)
            for x in matching:
                if not x in self.stats:
                    self.stats.append(x)

        # read the list of exprs, matching and applying to appropriate configs
        self.exprlist = []
        if prog.has_key('exprs'):
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

        if prog.has_key('sheets'):
            self.out_sheets = prog['sheets']
        else:
            self.out_sheets = [ ['all', 'full', ['*']] ]

        if prog.has_key('plots'):
            self.out_plots = prog['plots']
        else:
            self.out_plots = []

    # evaluates vals (stat and computed) for bench and returns dict
    # of values by fullname
    def evaluate_bench(self, bench):

        vals = {}

        # produce list of stat vals
        for c in self.configlist:
            for s in self.stats:
                if self.configs[c].runs.has_key(bench) and self.configs[c].runs[bench].stats.has_key(s):
                    st = self.configs[c].runs[bench].stats[s]
                    val = float(st.value())
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
        #print "eval: bench", bench
        while len(worklist) > 0:
            w = worklist.pop()
            e = exprs[w]
            if vals.has_key(w):
                oldval = vals[w]
            else:
                oldval = None
            #print "evaluate expr", w
            newval = e.evaluate(vals)
            #print " = ", newval
            if newval != oldval:
                vals[w] = newval
                for dest in self.affects[w]:
                    #if not dest in worklist:
                    #    print "--> ", dest
                    worklist.add(dest)

        return vals

    # evaluates all benches
    def evaluate(self):
        self.vals = {}
        for bench in self.benches:
            self.vals[bench] = self.evaluate_bench(bench)

    # produces sheets
    def output_sheets(self, sheetdir):
        for o in self.out_sheets:
            name, typ, l = o[0], o[1], o[2]

            output = open(sheetdir + '/' + name + '.csv', 'w')

            if typ == 'full':
                configs = []
                for c in l:
                    if c == '*': configs.extend(self.configlist)
                    else: configs.append(c)


                output.write("Bench,Config," + ','.join(self.stats + self.exprlist) + "\n")

                b = list(self.benches)
                b.sort()
                for bench in b:
                    for c in configs:
                        row = [bench, c]
                        for stat in self.stats + self.exprlist:
                            fullname = c + '.' + stat
                            if self.vals[bench].has_key(fullname):
                                val = self.vals[bench][fullname]
                            else:
                                val = None
                            if val == None: val = ''
                            row.append(str(val))
                        output.write(','.join(row) + "\n")
                    output.write("\n")

            elif typ == 'benchsummary':

                benchmap = self.benchmap
                benchnames = benchmap.values()
                benchnames.sort()
                benchinv = {}
                for k, v in benchmap.items():
                    benchinv[v] = k

                # expand statlist
                statlist = []
                for elem in l:

                    configspec, statspec = elem.split('.')
                    clist = []
                    slist = []

                    if configspec.find('*') != -1:
                        r = re.compile(configspec.replace('*', '.*'))
                        for c in self.configlist:
                            if r.match(c): clist.append(c)
                    else:
                        clist.append(configspec)
                    if statspec.startswith('{'):
                        for stat in statspec[1:-1].split(','):
                            stat = stat.strip()
                            slist.append(stat)
                    else:
                        slist.append(statspec)

                    for c in clist:
                        for s in slist:
                            statlist.append('%s.%s' % (c, s))

                output.write("Bench," + ','.join(statlist) + "\n")

                for benchname in benchnames:
                    bench = benchinv[benchname]
                    if bench in self.badbenches: continue
                    if not self.vals.has_key(bench): continue
                    row = [benchname]
                    for stat in statlist:
                        if self.vals[bench].has_key(stat):
                            val = self.vals[bench][stat]
                        else:
                            val = None
                        if val == None: val = ''
                        else: val = '%f' % val
                        row.append(val)
                    output.write(','.join(row) + "\n")

            output.close()

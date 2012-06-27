# dview/datalib/runs.py

try: import simplejson as json
except ImportError: import json
import os
import os.path
import sys
import glob

# a run is a single simulation that produces a collection of stats
class Run:
    def __init__(self, filename, statmap, rules):
        self.missing = True
        self.filename = filename
        try:
            self.dobj = json.load(open(filename))
            if self.try_accept(filename, self.dobj, statmap, rules):
                self.missing = False
            else:
                print "reject:", filename
                self.dobj = {}
        except:
            self.dobj = {}
        self.statmap = statmap
        self.stats = {}
        self.extract()

    def statval(self, dobj, statmap, statname):
        t = statmap.stattype(statname)
        if t is None: return None
        opts = statmap.opts[statname] if statmap.opts.has_key(statname) else None
        s = t(dobj, statname, opts)
        return s

    def try_accept(self, filename, dobj, statmap, rules):
        for r in rules:
            stat, rel, val = r
            v = self.statval(dobj, statmap, stat).value()
            s = "%f %s %f" % (v, rel, val)
            accept = eval(s)
            if not accept:
                return False
        return True

    def extract(self):
        for statname in self.dobj.keys():
            s = self.statval(self.dobj, self.statmap, statname)
            if s is None: continue
            self.stats[statname] = s

# a multirun is a set of simulations (Runs) of different checkpoints on the same benchmark
class MultiRun(Run):
    def __init__(self, runs, weights=None):
        self.runs = runs
        self.stats = {}
        self.weights = weights
        self.extract()

    def extract(self):

        if len(self.runs) == 0: return

        if self.weights != None: w = self.weights[i]
        else: w = [1.0 / len(self.runs)] * len(self.runs)

        statkeys = None
        for r in self.runs:
            s = set(r.stats.keys())
            if statkeys == None: statkeys = s
            else: statkeys = statkeys.intersection(s)
        stats = {}
        for s in statkeys:
            children = map(lambda r: r.stats[s], self.runs)
            stats[s] = CombinedStat(children, s, {})

# a config is a set of runs over many benchmarks
class Config:
    def __init__(self, directory, rules, yieldfunc=None, statmap=None, benches=None):

        self.directory = directory
        self.rules = rules
        self.statmap = statmap
        self.benches = benches
        self.runs = {}
        self.yieldfunc = yieldfunc

        if statmap is None:
            self.statmap = StatMap()

        if benches is None:
            self.benches = []
            for d in glob.glob(self.directory + '/*'):
                if not os.path.isdir(d): continue
                self.benches.append(os.path.basename(d))

        self.extract()

    def extract(self):
        stats = set()
        for b in self.benches:
            if not self.yieldfunc is None:
                self.yieldfunc()

            flist = self.autoconf(self.directory, b)

            runs = []
            for fi in flist:
                runs.append(Run(fi, self.statmap, self.rules))

            if len(runs) > 1:
                r = MultiRun(runs)
            elif len(runs) == 1:
                r = runs[0]
            else:
                r = Run('/dev/null', self.statmap, self.rules)

            self.runs[b] = r
            for stat in r.stats.keys():
                if not stat in stats:
                    stats.add(stat)
        self.stats = stats

    def autoconf(self, directory, bench):
        d = '%s/%s' % (directory, bench)
        if os.path.exists(d + '/sim.out'):
            return [d + '/sim.out']
        else:
            l = []
            for i in range(20):
                p = '%s/sim.%d.out' % (d, i)
                if os.path.exists(p):
                    l.append(p)
            return l

# a stat is a metric on a single benchmark run that can have either a scalar or
# vector value.
class Stat:
    def __init__(self, dobj, name, opts):
        self.dobj = dobj
        self.name = name
        self.opts = opts
        self.extract()

    def extract(self):
        pass

    def value(self):
        return 0.0

    def values(self):
        return []

# an AccumStat is a simple event count
class AccumStat(Stat):
    def extract(self):
        o = self.dobj[self.name]
        if type(o) == type({}):
            self._val = o['avg']
        elif type(o) == type(0):
            self._val = float(o)
        elif type(o) == type([]):
            if len(o) == 1:
                if type(o[0]) == type({}):
                    self._val = o[0]['avg']
                else:
                    self._val = o[0]
            else:
                self._val = 0.0

    def value(self):
        return self._val

    def values(self):
        return 

# a DistStat is a distribution
class DistStat(Stat):
    def extract(self):
        o = self.dobj[self.name]
        if type(o) == type([]):
            self._vals = o
            self._mean = 0.0
            c = 0
            for i in range(len(o)):
                c += o[i]
                self._mean += i * o[i]
            if c > 0: self._mean /= c
        else:
            self._vals = []
            self._mean = 0.0

    def value(self):
        return self._mean

    def values(self):
        return self._vals

class CombinedStat(Stat):
    def extract(self):
        self._vals = []
        for s in self.dobj:
            self._vals.append(s.value())
        self._mean = sum(self._vals) / len(self._vals) if len(self._vals) > 0 else 0.0

    def value(self):
        return self._mean

    def values(self):
        return self._vals

# a StatMap is an object that tells us what type of stat a given named stat is
class StatMap:
    def __init__(self):
        self.blacklist = ['version', 'cmdline']
        self.opts = {}
        pass

    def stattype(self, name):
        if name == 'version' or name == 'cmdline':
            return None
        elif '_by_' in name:
            return DistStat
        else:
            return AccumStat

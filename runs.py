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
            f = self._filename(self.directory, b)
            r = Run(f, self.statmap, self.rules)
            self.runs[b] = r
            for stat in r.stats.keys():
                if not stat in stats:
                    stats.add(stat)
        self.stats = stats


    def _filename(self, directory, bench):
        return '%s/%s/sim.out' % (directory, bench)

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

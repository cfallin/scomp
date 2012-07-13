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
        self.missing = True

    def extract(self):

        if len(self.runs) == 0: return

        if self.weights != None: w = self.weights
        else: w = None

        if w != None and len(self.runs) < len(w):
            return
        for r in self.runs:
            if r.missing:
                return
            if len(r.stats.keys()) == 0:
                return

        self.missing = False

        statkeys = set()
        for r in self.runs:
            s = set(r.stats.keys())
            statkeys = statkeys.union(s)
        stats = {}
        for s in statkeys:
            children = map(lambda r: r.stats[s] if r.stats.has_key(s) else 0.0, self.runs)
            stats[s] = CombinedStat(children, s, {}, w)

        self.stats = stats

    def try_accept(self, filename, dobj, statmap, rules):
        return True

# a config is a set of runs over many benchmarks
class Config:
    def __init__(self, directory, rules, yieldfunc=None, statmap=None, benches=None, multisep=False):

        self.directory = directory
        self.rules = rules
        self.statmap = statmap
        self.benches = benches
        self.runs = {}
        self.yieldfunc = yieldfunc
        self.multisep = multisep

        self.weights = {}
        self.read_weights()

        if statmap is None:
            self.statmap = StatMap()

        if benches is None:
            self.benches = []
            if not multisep:
                for d in glob.glob(self.directory + '/*'):
                    if not os.path.isdir(d): continue
                    self.benches.append(os.path.basename(d))
            else:
                for d in glob.glob(self.directory + '/*/sim.*.out'):
                    parts = d.split('/')
                    rootname = parts[-2]
                    idx = int(parts[-1].split('.')[1])
                    bname = '%s.%d' % (rootname, idx)
                    self.benches.append(bname)

        self.extract()

    def read_weights(self):
        fname = self.directory + '/../WEIGHTS.dat'
        if os.path.exists(fname):
            for line in open(fname).readlines():
                parts = line.split()
                bench = parts[0]
                weight = float(parts[2])
                if (not self.weights.has_key(bench)): self.weights[bench] = []
                self.weights[bench].append(weight)

    def extract(self):
        stats = set()
        for b in self.benches:
            if not self.yieldfunc is None:
                self.yieldfunc()

            flist = self.autoconf(self.directory, b)
            weights = None
            if self.weights.has_key(b):
                weights = self.weights[b]
            elif b.find('.') != -1 and self.weights.has_key(b.split('.', 1)[1]):
                weights = self.weights[b.split('.', 1)[1]]

            runs = []
            for fi in flist:
                r = Run(fi, self.statmap, self.rules)
                runs.append(r)

            if len(runs) > 1:
                r = MultiRun(runs, weights)
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
        if self.multisep:
            parts = bench.split('.')
            benchroot = '.'.join(parts[:-1])
            idx = int(parts[-1])
            d = '%s/%s/sim.%d.out' % (directory, benchroot, idx)
        else:
            d = '%s/%s/sim.out' % (directory, bench)
        if os.path.exists(d):
            return [d]
        else:
            l = []
            for i in range(10):
                p = '%s/%s/sim.%d.out' % (directory, bench, i)
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
        elif type(o) == type(0) or type(o) == type(0.0):
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
    def __init__(self, dobj, name, opts, weights):
        self._weights = weights
        Stat.__init__(self, dobj, name, opts)

    def extract(self):
        self._vals = []
        i = -1
        for s in self.dobj:
            i += 1
            if s != None:
                if self._weights != None:
                    self._vals.append(s.value() * self._weights[i])
                else:
                    self._vals.append(s.value())
                    
        if self._weights != None:
            self._mean = sum(self._vals)
        else:
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

# dview/datalib/runs.py

import simplejson as json
import os
import os.path
import glob

import stat

# a run is a single simulation that produces a collection of stats
class Run:
    def __init__(self, filename, statmap):
        self.missing = True
        try:
            self.dobj = json.load(open(filename))
            self.missing = False
        except:
            self.dobj = {}
        self.statmap = statmap
        self.stats = {}
        self.extract()

    def extract(self):
        for statname in self.dobj.keys():
            t = self.statmap.stattype(statname)
            if t is None: continue
            opts = self.statmap.opts[statname] if self.statmap.opts.has_key(statname) else None
            s = t(self.dobj, statname, opts)
            self.stats[statname] = t

# a config is a set of runs over many benchmarks
class Config:
    def __init__(self, directory, yieldfunc=None, statmap=None, benches=None):

        self.directory = directory
        self.statmap = statmap
        self.benches = benches
        self.runs = {}
        self.yieldfunc = yieldfunc

        if statmap is None:
            self.statmap = stat.StatMap()

        if benches is None:
            self.benches = []
            for d in glob.glob(self.directory + '/*'):
                if not os.path.isdir(d): continue
                self.benches.append(d)

        self.extract()

    def extract(self):
        for b in self.benches:
            if not self.yieldfunc is None:
                self.yieldfunc()
            f = self._filename(self.directory, b)
            r = Run(f, self.statmap)
            self.runs[b] = r

    def _filename(self, directory, bench):
        return '%s/%s/sim.out' % (directory, bench)

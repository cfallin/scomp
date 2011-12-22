# dview/datalib/stat.py

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
class AccumStat:
    def extract(self):
        o = self.dobj[self.name]
        if type(o) == type({}):
            self._val = o['avg']
        elif type(o) == type(0):
            self._val = float(o)
        elif type(o) == type([]):
            if len(o) == 1:
                self._val = float(o[0])
            else:
                self._val = 0.0

    def value(self):
        return self._val

    def values(self):
        return 

# a DistStat is a distribution
class DistStat:
    def extract(self):
        o = self.dobj[self.name]
        if type(o) == type([]):
            self._vals = o
            self._mean = 0.0
            c = 0
            for i in range(len(o)):
                c += o[i]
                self._mean += i * o[i]
            if c > 0: self.mean /= c
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

class Expr:
    def __init__(self):
        self.tokens = []
        self.deps = []
        self.idxmap = {}

    def parse(self, s, configname):

        # tokenize
        tokens = []
        in_name = False
        name = ''
        for c in s:
            if in_name:
                if c.isalnum() or c == '.' or c == '!' or c == '_':
                    name += c
                else:
                    tokens.append((True, name))
                    name = ''
                    in_name = False
            if not in_name:
                if c.isalpha() or c == '!' or c == '_':
                    in_name = True
                    name = c
                else:
                    tokens.append((False, c))

        if name != '':
            tokens.append((True, name))

        # find names in token list
        out = []
        deps = set()
        idxmap = {}
        for pair in tokens:
            if pair[0]: # if it's a name
                name = pair[1]
                if not '.' in name:
                    name = configname + '.' + name
                deps.add(name)
                if not idxmap.has_key(name): idxmap[name] = []
                idxmap[name].append(len(out))
                out.append(name)
            else:
                out.append(pair[1])

        self.tokens = out
        self.deps = deps
        self.idxmap = idxmap

        # return list of dependencies
        return list(self.deps)

    def evaluate(self, ctx):

        # substitute values for names
        out = list(self.tokens)
        for key in self.idxmap.keys():
            try:
                val = ctx[key]
            except:
                val = 0.0
            for idx in self.idxmap[key]:
                out[idx] = str(val)

        # reconstruct original expr and evaluate it
        s = ''.join(out)
        try:
            return eval(s, {}, {})
        except:
            return None

# --- test
# p = Expr()
# deps = p.parse('+1--3*(4*5-1)+ra.!IPC-base+!IPC+ra','ra')
# print 'deps: ', deps
# print p.evaluate({'ra.!IPC': 100.0, 'ra.base': 200.0, 'ra.ra': 300})

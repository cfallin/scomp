def parse(s, configname, ctx):

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

    print 'tokenized: ', tokens

    # substitute
    out = []
    for pair in tokens:
        if pair[0]:
            name = pair[1]
            print 'name', name
            if not '.' in name:
                name = configname + '.' + name
            print 'resolved to', name
            if not ctx.has_key(name):
                raise "Unknown variable " + name
            else:
                print 'with value', ctx[name]
                out.append(str(ctx[name]))
        else:
            out.append(pair[1])

    # reconstruct original expr
    s = ''.join(out)

    print 'subbed: ', s

    return eval(s, {}, {})

print parse('+1--3*(4*5-1)+ra.!IPC-base+!IPC+ra','ra', {'ra.!IPC': 100.0, 'ra.base': 200.0, 'ra.ra': 300})

# 58 + 100 - 200 + 100

from pyparsing import *

class ASTConst:
    def __init__(self, value):
        self.value = value
    def evaluate(self, configname, ctx):
        print 'eval constant: %f' % self.value
        return self.value
    def depends(self, configname):
        return []
    def __str__(self):
        return 'ASTConst(%f)' % self.value

class ASTIdent:
    def __init__(self, configname, colname):
        self.configname = configname
        self.colname = colname
    def evaluate(self, configname, ctx):
        c = self.configname
        if c == '': c = configname
        fullname = c + '.' + self.colname
        print 'eval ident: %s' % fullname
        if ctx.has_key(fullname):
            print 'has value: %f' % ctx[fullname]
            return ctx[fullname]
        else:
            print 'has no value'
            return None
    def depends(self, configname):
        c = self.configname
        if c == '': c = configname
        fullname = c + '.' + self.colname
        return [fullname]
    def __str__(self):
        return 'ASTIdent(%s.%s)' % (self.configname, self.colname)

class ASTOp:
    def __init__(self, operator, val1, val2):
        self.operator = operator
        self.val1 = val1
        self.val2 = val2
    def evaluate(self, configname, ctx):
        val1 = None
        val2 = None
        if self.val1 != None: val1 = self.val1.evaluate(configname, ctx)
        if self.val2 != None: val2 = self.val2.evaluate(configname, ctx)

        print 'evaluate op %s (val1 %s val2 %s)' % (self.operator, str(val1), str(val2))

        if self.operator == '+':
            if val1 is None or val2 is None: return None
            return val1 + val2
        if self.operator == '-':
            if val1 is None or val2 is None: return None
            return val1 - val2
        if self.operator == '*':
            if val1 is None or val2 is None: return None
            return val1 * val2
        if self.operator == '/':
            if val1 is None or val2 is None: return None
            if val2 == 0.0: return None
            return val1 / val2
        if self.operator == 'unary-':
            if val1 is None: return None
            return -val1
        if self.operator == 'unary+':
            return val1

        return None
    def depends(self, configname):
        d = []
        if self.val1 != None: d.extend(val1.depends(configname))
        if self.val2 != None: d.extend(val2.depends(configname))
        return d
    def __str__(self):
        return 'ASTOp(%s,%s,%s)' % (self.operator, str(self.val1), str(self.val2))

integer = Word(nums)
real = Combine(Word(nums) + "." + Word(nums))
bareIdent = Word(alphas + '_', bodyChars = alphanums+'_')
fieldIdent = Word(alphas + '_!', bodyChars = alphanums+'_')
qualifiedIdent = bareIdent + "." + fieldIdent

integer.setParseAction(lambda tok: ASTConst(float(tok[0])))
real.setParseAction(lambda tok: ASTConst(float(tok[0])))
fieldIdent.setParseAction(lambda tok: ASTIdent('', str(tok[0])))
qualifiedIdent.setParseAction(lambda tok: ASTIdent(str(tok[0]), tok[2].colname))

operand = Forward()
baseOperand = real | integer | qualifiedIdent | fieldIdent
signedOperand = oneOf('- +') + baseOperand
operand << (signedOperand | baseOperand)

signedOperand.setParseAction(lambda tok: ASTOp('unary' + str(tok[0]), tok[1], None))

term = Forward()
expr = Forward()
parenExpr = Forward()

parenExpr << ("(" + expr + ")")
term << ( (operand | parenExpr) + Group(OneOrMore(oneOf('- +') + (operand | parenExpr))) )
expr << ( (term + Group(OneOrMore(oneOf('* /') + term))) | term )

def parseSeq(tok):
    print 'parseSeq', tok
    astroot = tok[0]
    tok = tok[1:]
    while len(tok) >= 2:
        op, val = tok[0:2]
        tok = tok[2:]
        astroot = ASTOp(op, astroot, val)
    return astroot

term.setParseAction(lambda tok: parseSeq(tok))
expr.setParseAction(lambda tok: parseSeq(tok))
parenExpr.setParseAction(lambda tok: tok[1])

ast = expr.parseString('+1--3*(4*5-1)+ra.!IPC-base+!IPC', parseAll=True).asList()[0]

# 58 + 100 - 200 + 100

print ast.evaluate('ra', {'ra.!IPC': 100.0, 'ra.base': 200.0})

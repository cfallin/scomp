#!/usr/bin/env python

import os
import os.path
import glob
import sys

class err:
    def __init__(self, s = ''):
        self.s = s
    def __str__(self):
        return self.s

def install(binpath):
    if not (os.path.exists(binpath) and os.path.isdir(binpath)):
        raise err("Binary path %s does not exist or is not a directory." % binpath)

    pypath = os.path.abspath(binpath) + '/scomp_modules'

    if not os.path.exists(pypath):
        os.mkdir(pypath)

    for x in glob.glob('*.py'):
        if x == 'setup.py': continue
        os.system("cp %s %s" % (x, pypath + '/' + x))

    f = open(os.path.abspath(binpath) + '/scomp', 'w')
    f.write("""#!/bin/sh
export PYTHONPATH=%s:$PYTHONPATH
python %s "$@"
""" % (pypath, pypath + '/scomp.py'))
    f.close()
    os.system('chmod +x %s' % (os.path.abspath(binpath) + '/scomp'))

if len(sys.argv) > 1:
    install(sys.argv[1])
else:
    install('/usr/local/bin')

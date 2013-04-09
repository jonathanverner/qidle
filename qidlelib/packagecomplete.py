import sys
import os
def _packages(path, prefix=''):
    ret = [ prefix+name[:-3] for name in os.listdir(path) if name.endswith('.py') and name != '__init__.py' ]
    for pyc in [ prefix+name[:-4] for name in os.listdir(path) if name.endswith('.pyc') and name != '__init__.pyc' ]:
        if pyc not in ret:
            ret.append(pyc)
    for so in [ prefix+name[:-3] for name in os.listdir(path) if name.endswith('.so') and name != '__init__.so' ]:
        if so not in ret:
            ret.append(so)
    for subp in [ name for name in os.listdir(path) if os.path.isdir(os.path.join(path,name)) and os.path.exists(os.path.join(path,name,'__init__.py')) ]:
        ret += [subp]
        ret += _packages( os.path.join(path, subp), subp+'.' )
    return ret

def find_packages():
    ret = []
    for p in sys.path:
        if os.path.exists(p):
            ret += _packages(p)
    return ret

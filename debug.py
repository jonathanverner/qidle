import sys
def debug(*args):
    for a in args:
        try:
            sys.__stdout__.write(str(a))
        except Exception, e:
            sys.__stdout__.write("Debug::Exception:"+str(e))
        sys.__stdout__.write(' ')
    sys.__stdout__.write("\n")

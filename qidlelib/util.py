from sys import version_info
if version_info[0] < 3:
    str_type = unicode
    python_3 = False
else:
    str_type = str
    python_3 = True

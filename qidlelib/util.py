from sys import version_info
import gzip
import re
from qidlelib.config import config

if version_info[0] < 3:
    str_type = unicode
    python_3 = False
else:
    str_type = str
    python_3 = True

CODING_PATTERN = re.compile("coding: *([^ ]+)", re.IGNORECASE | re.UNICODE)


def gzopen(fname, mode):
    """ Opens the file @fname in mode @mode and returns the file object.
        If @fname ends with '.gz', transparently decompresses it (using
        the gzip library, i.e. the object returned is in fact not the
        standard file object in this case).
    """
    if fname.endswith('.gz'):
        return gzip.open(fname,mode)
    else:
        return open(fname,mode)

def load_script_to_unicode(fname):
    """ Loads the filename @fname and converts it to unicode.
        The encoding is guessed from a coding: line in the file
        or the default_encoding in the config file is used.
        If both fail, utf-8 is tried. If everything fails,
        a string object is returned. """
    script = open(unicode(fname),'rb').read()
    try:
        matches = CODING_PATTERN.findall(script)
        if len(matches) > 0:
            ret = unicode(script,encoding=matches[0])
        else:
            ret = unicode(script, encoding=config.default_encoding)
    except:
        try:
            ret = unicode(script,encoding='utf-8')
        except:
            ret = script
    return ret

def save_script_from_unicode(fname, script):
    """ Saves the script @script to the file @fname. The encoding
        is guessed from the a coding: line if present in the script,
        otherwise the default_encoding form the config file is used
        or utf-8 if it is not set. If none of this succeeds, saves
        the file as ASCII deleting non-ASCII characters!! No error
        is given in this case !!!
    """
    try:
        matches = CODING_PATTERN.findall(script)
        if len(matches) > 0:
            string = script.encode(encoding=matches[0])
        else:
            string = script.encode(encoding=config.default_encoding)
    except:
        try:
            string = script.encode(encoding='utf-8')
        except:
            string = script.encode(encoding='ascii',errors='ignore')
    f = open(fname,'wb')
    f.write(string)
    f.close()

def substr(s, start_pos, end_chars, direction=1):
    """ Returns the largest substring of s which starts
        at start_pos, does not include any character from end_chars
        and extends to the left (if direction = -1) or to
        the right (if direction = 1) """
    ret = []
    pos = start_pos
    while ( 0 <= pos < len(s) and s[pos] not in end_chars):
        ret.append(s[pos])
        pos += direction

    if direction < 0:
        ret.reverse()
    return "".join(ret)

def last_unmatched_char(s, chars):
    """ Returns the position of the last unbalanced character from @chars
        in @s or None if all characters from chars come in pairs.
        @chars is a list of pairs (opening_char, closing_char)

        >>> s = "def ahoj('', \"\\\"Jak"
        >>> matchings = [('(',')'),('"','"'),("'","'")]
        >>> last_unmatched_char(s,matchings)
        13
        >>>

    """
    counters = {}
    opening = []
    closing = []
    close_to_open = {}
    for c in chars:
        counters[c] = []

    for o,c in chars:
        opening.append(o)
        closing.append(c)
        close_to_open[c] = o
        counters[o] = []

    prev_backslash = False
    for pos in range(len(s)):
        if prev_backslash:
            prev_backslash = False
            continue
        if s[pos] == '\\':
            prev_backslash = True
            continue
        if s[pos] in opening:
            if s[pos] not in closing:
                counters[s[pos]].append(pos)
            else:
                try:
                    counters[s[pos]].pop()
                except:
                    counters[s[pos]].append(pos)
        elif s[pos] in closing:
            try:
                counters[close_to_open[s[pos]]].pop()
            except:
                pass
    last_pos = -1
    for unmatched_pos in counters.values():
        if len(unmatched_pos) > 0 and last_pos < unmatched_pos[-1]:
            last_pos = unmatched_pos[-1]
    if last_pos < 0:
        return None
    else:
        return last_pos





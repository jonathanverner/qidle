from PyQt4.QtGui import QTextBlockUserData, QTextBlock, QTextCursor


class TextBlockData(QTextBlockUserData):

    def __init__(self):
        QTextBlockUserData.__init__(self)
        self.data = {}

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def __str__(self):
        return str(self.data)


def block_type_for_stream(stream):
    if stream == "stdout":
        return TextBlock.TYPE_OUTPUT_STDOUT
    elif stream == "stderr":
        return TextBlock.TYPE_OUTPUT_STDERR
    elif stream == "msg":
        return TextBlock.TYPE_OUTPUT_MSG
    return TextBlock.TYPE_OUTPUT_STDOUT


class TextBlock(object):

    TYPE_CODE_START = 0
    TYPE_CODE_CONTINUED = 1
    TYPE_OUTPUT_STDOUT = 2
    TYPE_OUTPUT_STDERR = 3
    TYPE_OUTPUT_MSG = 4
    TYPE_MESSAGE = 5
    TYPE_RAW_INPUT = 6
    TYPE_OUTPUT_STDOUT_HTML = 7
    TYPE_NONE = None

    EDITABLE_TYPES = [TYPE_CODE_START, TYPE_CODE_CONTINUED, TYPE_RAW_INPUT]
    CODE_TYPES = [TYPE_CODE_START, TYPE_CODE_CONTINUED]

    CODE_START_PROMPT = "<span style='color:darkRed'>>>></span> "
    CODE_CONTINUE_PROMPT = " "*4

    CODE_INDENT = " "*4

    WORD_STOP_CHARS = " ~!@#$%^&*()+{}|:\"<>?,/;'[]\\-="

    def __init__(self, data, create_new=False, typ=None):
        if isinstance(data, QTextBlock):
            self.block = data
        elif isinstance(data, QTextCursor):
            if create_new:
                self.block = data.insertBlock()
            self.block = data.block()
        else:
            raise Exception("Invalid data to initialize block (must be a QTextBlock or QTextCursor), is "+str(
                type(data))+" instead.")
        self.annotations = self.block.userData()
        if self.annotations is None:
            self.annotations = TextBlockData()
            self.block.setUserData(self.annotations)
        self._initializeDefaults()
        if create_new:
            self.setType(typ)
            # debug("TextObject.__init__: created new object")
            # debug(str(self))
        if not 'type' in self.annotations.keys():
            self.annotations['type'] = self.TYPE_NONE

    def deleteBlock(self):
        c = self.endCursor()
        for i in range(len(self.block.text())):
            c.deletePreviousChar()
        c.deletePreviousChar()

    def __str__(self):
        ret = "Typ               : " + str(self.type) + "\n"
        ret += "Start Pos         :" + str(
            self.startCursor().position()) + "\n"
        ret += "End Pos           :" + str(self.endCursor().position()) + "\n"
        ret += "Content           :" + self.content() + "\n"
        ret += "full content      :" + self.content(
            include_decoration=True)+"\n"
        ret += "Active area start :" + str(self.startCursor(
            in_active_area=True).position())+"\n"
        ret += "indent level      :" + str(self.indentLevel()) + "\n"
        ret += "indent string     :" + self.indent_string + ";\n"
        return ret

    def isFirst(self):
        return self.block.position == 0

    def isLast(self):
        return not self.next().block.isValid()

    def firstSameBlock(self):
        if self.type == TextBlock.TYPE_CODE_START:
            return self
        elif self.type == TextBlock.TYPE_CODE_CONTINUED:
            ret = self
            while ret.type != TextBlock.TYPE_CODE_START and not ret.isFirst():
                ret = ret.previous()
            return ret
        else:
            ret = self
            prev = ret.previous()
            while prev.type == self.type and not ret.isFirst():
                ret = prev
                prev = prev.previous()
            return ret

    def lastSameBlock(self):
        if self.type == TextBlock.TYPE_CODE_START:
            tp = TextBlock.TYPE_CODE_CONTINUED
        else:
            tp = self.type
        ret = self
        nxt = ret.next()
        while nxt.type == tp and not ret.isLast():
            ret = nxt
            nxt = nxt.next()
        return ret

    def previous(self):
        return TextBlock(self.block.previous())

    def next(self):
        return TextBlock(self.block.next())

    def relatedBlocks(self):
        if self.type in self.CODE_TYPES:
            return self.relatedCodeBlocks()
        elif self.type == self.TYPE_RAW_INPUT:
            return self.relatedInputBlocks()
        return []

    def isCursorInRelatedBlock(self, cursor):
        related = self.relatedBlocks()
        if len(related) == 0:
            return False
        return related[0].startCursor() <= cursor <= related[-1].endCursor()

    def isCursorInRelatedCodeBlock(self, cursor):
        related = self.relatedCodeBlocks()
        if len(related) == 0:
            return False
        return related[0].startCursor() <= cursor <= related[-1].endCursor()

    def relatedCodeBlocks(self, only_previous=False):
        ret = []
        b = self
        while b.type in [self.TYPE_CODE_CONTINUED, self.TYPE_CODE_START]:
            ret.append(b)
            if b.type == self.TYPE_CODE_START or b.block.position() == 0:
                break
            b = b.previous()
        ret.reverse()
        if only_previous:
            return ret
        b = self.next()
        while b.type == self.TYPE_CODE_CONTINUED:
            if b.block.position() == 0:
                break
            ret.append(b)
            b = b.next()
        return ret

    def relatedInputBlocks(self):
        return [self]

    def _initializeDefaults(self):
        if 'decorated' not in self.annotations.keys():
            self.decorated = False
        if 'active_area_start' not in self.annotations.keys():
            self.active_area_start = 0
        if 'indent_string' not in self.annotations.keys():
            self.indent_string = self.CODE_INDENT

    def _decorate(self, decoration):
        c = QTextCursor(self.block)
        spos = c.positionInBlock()
        if decoration.count(" ") == len(decoration):
            c.insertText(decoration)
        else:
            c.insertHtml(decoration)
        self.decorated = True
        self.decoration_len = c.positionInBlock()-spos
        self.active_area_start = self.decoration_len

    def _unDecorate(self):
        if self.decorated:
            c = QTextCursor(self.block)
            for i in range(self.decoration_len):
                c.deleteChar()
            self.active_area_start -= self.decoration_len

    def wordUnderCursor(self, cursor):
        """Note: Doesn't check that the cursor is in the current block """
        full_content = self.content(include_decoration=True)
        cpos = min(cursor.positionInBlock(), len(full_content)-1)
        pos = cpos
        ret = []
        while(pos >= self.active_area_start and full_content[pos] not in TextBlock.WORD_STOP_CHARS):
            ret.append(full_content[pos])
            pos -= 1
        ret.reverse()
        pos = cpos+1
        while(pos < len(full_content) and full_content[pos] not in TextBlock.WORD_STOP_CHARS):
            ret.append(full_content[pos])
            pos += 1
        return "".join(ret)

    def unIndent(self):
        content = self.content()
        if content.startswith(self.indent_string):
            c = self.startCursor()
            for i in range(len(self.indent_string)):
                c.deleteChar()

    def indent(self, n=1):
        c = self.startCursor()
        for i in range(n):
            c.insertText(self.indent_string)

    def indentLevel(self):
        content = self.content()
        level = 0
        while content[level*len(self.indent_string):].startswith(self.indent_string):
            level += 1
        return level

    def blockLeadingPosition(self):
        return self.active_area_start + self.indentLevel() * len(self.indent_string)

    def isInLeadingPosition(self, cursor):
        return cursor.positionInBlock() == self.blockLeadingPosition()

    def cursorSelectToLeadingPosition(self, cursor):
        delta = cursor.positionInBlock()-self.blockLeadingPosition()
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, delta)

    def leadingCursor(self):
        c = self.startCursor()
        c.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor,
                       self.indentLevel() * len(self.indent_string))
        return c

    def cursorAt(self, position, in_active_area=True):
        c = QTextCursor(self.block)
        p = min(position, self.length-1)
        if in_active_area:
            p = max(p, self.active_area_start)
        c.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, p)
        return c

    def startCursor(self, in_active_area=True):
        c = QTextCursor(self.block)
        if in_active_area:
            c.movePosition(
                QTextCursor.Right, QTextCursor.MoveAnchor, self.active_area_start)
        return c

    def endCursor(self):
        c = self.startCursor()
        c.movePosition(QTextCursor.EndOfBlock)
        return c

    def containsCursor(self, cursor, in_active_area=True):
        """ Returns true if the cursor is in the current block's active area
            (default) or in the current block (in_active_area = False) """
        if in_active_area == 'strict':
            ret = self.startCursor(in_active_area) < cursor <= self.endCursor()
        else:
            ret = self.startCursor(
                in_active_area) <= cursor <= self.endCursor()
        # debug("containsCursor: ", cursor.position(), " in [",
        # self.startCursor(in_active_area).position(),
        # ",",self.endCursor().position(),"], result:", ret)
        return ret

    def setType(self, typ):
        self._unDecorate()
        self.type = typ
        if typ == self.TYPE_CODE_START:
            self._decorate(self.CODE_START_PROMPT)
        elif typ == self.TYPE_CODE_CONTINUED:
            self._decorate(self.CODE_CONTINUE_PROMPT)
        elif typ == self.TYPE_RAW_INPUT:
            self.active_area_start = self.block.length()-1

    def getType(self):
        return self.type

    @property
    def length(self):
        return self.block.length()

    def activeContent(self):
        return unicode(self.block.text())[self.active_area_start:]

    def content(self, include_decoration=False):
        if include_decoration or not self.decorated:
            spos = 0
        else:
            spos = self.decoration_len
        return unicode(self.block.text())[spos:]

    def contentToCursor(self, cursor, include_decoration=False, in_active_area=False):
        if cursor <= self.startCursor(self, in_active_area=in_active_area):
            return ""
        if in_active_area:
            spos = self.active_area_start
        elif include_decoration or not self.decorated:
            spos = 0
        else:
            spos = self.decoration_len
        if self.containsCursor(cursor, in_active_area):
            epos = cursor.positionInBlock()
        else:
            epos = -1
        return unicode(self.block.text())[spos:epos]

    def contentFromCursor(self, cursor):
        spos = cursor.positionInBlock()
        return unicode(self.block.text())[spos:]

    def appendText(self, text):
        c = self.endCursor()
        c.insertText(text)

    def appendHtml(self, html):
        c = self.endCursor()
        c.insertHtml(html)

    def __getattr__(self, key):
        if key == 'annotations' or key == 'block':
            raise AttributeError(key)
        try:
            return self.annotations[key]
        except KeyError as e:
            raise AttributeError(e)

    def __setattr__(self, key, val):
        if key == 'annotations' or key == 'block':
            object.__setattr__(self, key, val)
        else:
            self.annotations[key] = val

    def __getitem__(self, key):
        return self.annotations[key]

    def __setitem__(self, key, value):
        self.annotations[key] = value

    def __delitem__(self, key):
        del self.annotations[key]

    def keys(self):
        return self.annotations.keys()

    def items(self):
        return self.annotations.items()

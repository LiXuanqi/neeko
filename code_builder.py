class CodeBuilder:
    INDENT_STEP = 4

    def __init__(self, indent=0):
        self.code = []
        self.indentLevel = indent

    def addLine(self, line):
        self.code.extend([" " * self.indentLevel, line, "\n"])

    def indent(self):
        self.indentLevel += self.INDENT_STEP

    def dedent(self):
        self.indentLevel -= self.INDENT_STEP

    def addSection(self):
        section = CodeBuilder(self.indentLevel)
        self.code.append(section)
        return section

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def getGlobals(self):
        assert self.indentLevel == 0
        source = str(self)
        globalNamespace = {}
        exec (source, globalNamespace)
        return globalNamespace

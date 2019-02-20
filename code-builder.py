import re


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


class Template:

    def __init__(self, text, *contexts):
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.allVars = set()
        self.loopVars = set()

        code = CodeBuilder()
        code.addLine("def render(context, doDots):")
        code.indent()
        varsCode = code.addSection()
        code.addLine("result = []")
        code.addLine("appendToResult = result.append")
        code.addLine("extendToResult = result.extend")
        code.addLine("toStr = str")

        buffered = []

        def flushOutput():
            if len(buffered) == 1:
                code.addLine("appendToResult(%s)" % buffered[0])
            elif len(buffered) > 1:
                code.addLine("extendToResult([%s])" % ", ".join(buffered))
            del buffered[:]

        opsStack = []

        # - handle Tokens
        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:
            if token.startswith("{#"):
                # Comment
                continue
            elif token.startswith("{{"):
                # Expression
                expression = self._expr_code(token[2:-2].strip())
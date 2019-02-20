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
                # - Comment
                continue
            elif token.startswith("{{"):
                # - Expression
                expression = self._exprCode(token[2:-2].strip())
                buffered.append("toStr(%s)" % expression)
            elif token.startswith("{%"):
                # - Tag
                flushOutput()
                words = token[2:-2].strip().split()
                if words[0] == "if":
                    # - If statement
                    if len(words) != 2:
                        self._syntaxError("Invalid If Statement", token)
                    opsStack.append("if")
                    code.addLine("If %s" % self._exprCode(words[1]))
                    code.indent()
                elif words[0] == "for":
                    # - Loop statement
                    if len(words) != 4 or words[2] != "in":
                        self._syntaxError("Invalid For Statement", token)
                    opsStack.append("for")
                    self._variable(words[1], self.loopVars)
                    code.addLine("for c_%s in %s" % (words[1], self._exprCode(words[3])))
                    code.indent()
                elif words[0].startswith("end"):
                    # - End tag
                    if len(words) != 1:
                        self._syntaxError("Invalid End Statement", token)
                    endWhat = words[0][3:]
                    if not opsStack:
                        self._syntaxError("Too many ends", token)
                    startWhat = opsStack.pop()
                    if startWhat != endWhat:
                        self._syntaxError("Mismatched end tag", endWhat)
                    code.dedent()
                else:
                    self._syntaxError("Don't understand tag", words[0])
            else:
                # - Literal content
                if token:
                    buffered.append(repr(token))

        if opsStack:
            self._syntaxError("Unmatched action tag", opsStack[-1])

        flushOutput()

        for varName in self.allVars - self.loopVars:
            varsCode.addLine("c_%s = context[%r]" % (varName, varName))

        code.addLine("return ''.join(result)")
        code.dedent()

        self._render_funcition = code.getGlobals()['render']

    def _syntaxError(self, msg, token):
        raise TemplateSyntaxError("%s: %r" % (msg, token))

    def _exprCode(self, expr):
        if "|" in expr:
            pipes = expr.split("|")
            code = self._exprCode(pipes[0])
            for pipe in pipes[1:]:
                self._variable(pipe, self.allVars)
                code = "c_%s(%s)" % (pipe, code)
        elif "." in expr:
            dots = expr.split(".")
            code = self._exprCode(dots[0])
            args = ", ".join(repr(dot) for dot in dots[1:])
            code = "do_dots(%s, %s)" % (code, args)
        else:
            self._variable(expr, self.allVars)
            code = "c_%s" % expr
        return code


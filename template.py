import re

from code_builder import CodeBuilder
from errors import TemplateSyntaxError


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
                    code.addLine("if %s:" % self._exprCode(words[1]))
                    code.indent()
                elif words[0] == "for":
                    # - Loop statement
                    if len(words) != 4 or words[2] != "in":
                        self._syntaxError("Invalid For Statement", token)
                    opsStack.append("for")
                    self._variable(words[1], self.loopVars)
                    code.addLine("for c_%s in %s:" % (words[1], self._exprCode(words[3])))
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

        self._renderFuncition = code.getGlobals()['render']

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
            code = "doDots(%s, %s)" % (code, args)
        else:
            self._variable(expr, self.allVars)
            code = "c_%s" % expr
        return code

    def _variable(self, name, varsSet):
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntaxError("The param's name is invalid.", name)
        varsSet.add(name)

    def render(self, context=None):
        renderContext = dict(self.context)
        if context:
            renderContext.update(context)
        return self._renderFuncition(renderContext, self._doDots)

    def _doDots(self, value, *dots):
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value

import re

import pytest

from errors import TemplateSyntaxError
from template import Template


def tryRender(text, ctx=None, expected=None):
    actual = Template(text).render(ctx or {})
    if expected:
        assert actual == expected


def assertSyntaxError(text, ctx=None, msg=None):
    with pytest.raises(TemplateSyntaxError) as excinfo:
        tryRender(text, ctx)
    assert str(excinfo.value) == msg


def test_passthrough():
    tryRender("Hello.", {}, "Hello.")
    tryRender("Hello, 20% fun time!", {}, "Hello, 20% fun time!")


def test_variables():
    tryRender("Hello, {{name}}!", {'name': '1_x7'}, "Hello, 1_x7!")


def test_undefined_variables():
    with pytest.raises(KeyError):
        tryRender("Hi, {{name}}!")


def test_pipes():
    data = {
        'name': 'Ned',
        'upper': lambda x: x.upper(),
        'second': lambda x: x[1],
    }
    tryRender("Hello, {{name|upper}}!", data, "Hello, NED!")
    tryRender("Hello, {{name|upper|second}}!", data, "Hello, E!")


def test_reusability():
    globs = {
        'upper': lambda x: x.upper(),
        'punct': '!',
    }
    template = Template("This is {{name|upper}}{{punct}}", globs)
    assert template.render({'name': 'Ned'}) == "This is NED!"
    assert template.render({'name': 'Ben'}) == "This is BEN!"


def test_attributes():
    obj = AnyOldObject(a="Ay")
    tryRender("{{obj.a}}", locals(), "Ay")
    obj2 = AnyOldObject(obj=obj, b="Bee")
    tryRender("{{obj2.obj.a}} {{obj2.b}}", locals(), "Ay Bee")


def test_member_function():
    class WithMemberFns(AnyOldObject):
        def ditto(self):
            return self.txt + self.txt

    obj = WithMemberFns(txt="Once")
    tryRender("{{obj.ditto}}", locals(), "OnceOnce")


def test_dict():
    d = {'a': 17, 'b': 23}
    tryRender("{{d.a}} < {{d.b}}", locals(), "17 < 23")


def test_loops():
    nums = [1, 2, 3, 4]
    tryRender(
        "Look: {% for n in nums %}{{n}}, {% endfor %}done.",
        locals(),
        "Look: 1, 2, 3, 4, done."
    )


def test_loops_with_pipes():
    nums = [1, 2, 3, 4]

    def rev(l):
        l = l[:]
        l.reverse()
        return l

    tryRender(
        "Look: {% for n in nums|rev %}{{n}}, {% endfor %}done.",
        locals(),
        "Look: 4, 3, 2, 1, done."
    )


def test_empty_loops():
    tryRender(
        "Empty: {% for n in nums %}{{n}}, {% endfor %}done.",
        {'nums': []},
        "Empty: done."
    )


def test_multiline_loops():
    tryRender(
        "Look: \n{% for n in nums %}\n{{n}}, \n{% endfor %}done.",
        {'nums': [1, 2, 3]},
        "Look: \n\n1, \n\n2, \n\n3, \ndone."
    )


def test_multiple_loops():
    tryRender(
        "{% for n in nums %}{{n}}{% endfor %} and "
        "{% for n in nums %}{{n}}{% endfor %}",
        {'nums': [1, 2, 3]},
        "123 and 123"
    )


def test_comments():
    tryRender(
        "Hello, {# Name goes here: #}{{name}}!",
        {'name': 'Ned'}, "Hello, Ned!"
    )
    tryRender(
        "Hello, {# Name\ngoes\nhere: #}{{name}}!",
        {'name': 'Ned'}, "Hello, Ned!"
    )


def test_if():
    tryRender(
        "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
        {'ned': 1, 'ben': 0},
        "Hi, NED!"
    )
    tryRender(
        "Hi, {% if ned %}NED{% endif %}{% if ben %}BEN{% endif %}!",
        {'ned': 0, 'ben': 1},
        "Hi, BEN!"
    )
    tryRender(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {'ned': 0, 'ben': 0},
        "Hi, !"
    )
    tryRender(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {'ned': 1, 'ben': 0},
        "Hi, NED!"
    )
    tryRender(
        "Hi, {% if ned %}NED{% if ben %}BEN{% endif %}{% endif %}!",
        {'ned': 1, 'ben': 1},
        "Hi, NEDBEN!"
    )


def test_complex_if():
    class Complex(AnyOldObject):
        """A class to try out complex data access."""

        def getit(self):
            """Return it."""
            return self.it

    obj = Complex(it={'x': "Hello", 'y': 0})
    tryRender(
        "@"
        "{% if obj.getit.x %}X{% endif %}"
        "{% if obj.getit.y %}Y{% endif %}"
        "{% if obj.getit.y|str %}S{% endif %}"
        "!",
        {'obj': obj, 'str': str},
        "@XS!"
    )


def test_loop_if():
    tryRender(
        "@{% for n in nums %}{% if n %}Z{% endif %}{{n}}{% endfor %}!",
        {'nums': [0, 1, 2]},
        "@0Z1Z2!"
    )
    tryRender(
        "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
        {'nums': [0, 1, 2]},
        "X@012!"
    )
    tryRender(
        "X{%if nums%}@{% for n in nums %}{{n}}{% endfor %}{%endif%}!",
        {'nums': []},
        "X!"
    )


def test_nested_loops():
    tryRender(
        "@"
        "{% for n in nums %}"
        "{% for a in abc %}{{a}}{{n}}{% endfor %}"
        "{% endfor %}"
        "!",
        {'nums': [0, 1, 2], 'abc': ['a', 'b', 'c']},
        "@a0b0c0a1b1c1a2b2c2!"
    )


def test_exception_during_evaluation():
    with pytest.raises(TypeError):
        tryRender("Hey {{foo.bar.baz}} there", {'foo': None}, "Hey ??? there")


def test_bad_names():
    assertSyntaxError("Wat: {{ var%&!@ }}", {}, "The param's name is invalid.: 'var%&!@'")
    assertSyntaxError("Wat: {{ foo|filter%&!@ }}", {}, "The param's name is invalid.: 'filter%&!@'")
    assertSyntaxError("Wat: {% for @ in x %}{% endfor %}", {}, "The param's name is invalid.: '@'")


def test_bogus_tag_syntax():
    assertSyntaxError("Huh: {% bogus %}!!{% endbogus %}??", {}, "Don't understand tag: 'bogus'")


def test_malformed_if():
    assertSyntaxError("Buh? {% if %}hi!{% endif %}", {}, "Invalid If Statement: '{% if %}'")
    assertSyntaxError("Buh? {% if this or that %}hi!{% endif %}", {}, "Invalid If Statement: '{% if this or that %}'")


def test_malformed_for():
    assertSyntaxError("Weird: {% for %}loop{% endfor %}", {}, "Invalid For Statement: '{% for %}'")
    assertSyntaxError("Weird: {% for x from y %}loop{% endfor %}", {}, "Invalid For Statement: '{% for x from y %}'")
    assertSyntaxError("Weird: {% for x, y in z %}loop{% endfor %}", {}, "Invalid For Statement: '{% for x, y in z %}'")


def test_bad_nesting():
    assertSyntaxError("{% if x %}X", {}, "Unmatched action tag: 'if'")
    assertSyntaxError("{% if x %}X{% endfor %}", {}, "Mismatched end tag: 'for'")
    assertSyntaxError("{% if x %}{% endif %}{% endif %}", {}, "Too many ends: '{% endif %}'")


def test_malformed_end():
    assertSyntaxError("{% if x %}X{% end if %}", {}, "Invalid End Statement: '{% end if %}'")
    assertSyntaxError("{% if x %}X{% endif now %}", {}, "Invalid End Statement: '{% endif now %}'")


class AnyOldObject:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

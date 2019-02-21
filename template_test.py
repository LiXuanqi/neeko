from code_builder import Template

def testPureHtml():
    html = "<p>Hello world!</p>"
    text = Template(html).render()
    assert text == html

def testVar():
    html = "<p>Hello {{ name }}!</p>"
    text = Template(html).render({
        'name': '1_x7'
    })
    assert text == "<p>Hello 1_x7!</p>"

def testIf():
    html = """
    {% if visible %}
    <span>You can see me.</span>
    {% endif %}
    <span>Always Visible!</span>
    """
    text = Template(html).render({
        'visible': True
    })
    assert text == """
    <span>You can see me.</span>
    <span>Always Visible!</span>
    """

def testFor():
    html = """
    {% for item in items %}
    <span>{{ item }}/span>
    {% endfor %}
    """
    text = Template(html).render({
        'items': [1, 2, 3, 4]
    })
    assert text == """
    <span>1</span>
    <span>2</span>
    <span>3</span>
    <span>4</span>
    """

def testPipe():
    html = "<span>{{ name|upper }}</span>"
    text = Template(html).render({
        'name': 'lxq'
    })
    assert text == "<span>LXQ</span>"

def testPipeWithSpace():
    html = "<span>{{ name  |  upper }}</span>"
    text = Template(html).render({
        'name': 'lxq'
    })
    assert text == "<span>LXQ</span>"
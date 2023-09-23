from parametrization import Parametrization

from simpukka import template

def simple_templating():
    return "John"

@Parametrization.autodetect_parameters()
@Parametrization.default_parameters(filter_level=template.FilterLevel.disabled)
@Parametrization.case(name="No templating", text="Hello world!", data={}, result="Hello world!")
@Parametrization.case(name="Simple templating - Variable", text="Hello, ((user.name))!", data={"user": {"name": "John"}}, result="Hello, John!")
@Parametrization.case(name="Simple templating - Function", text="Hello, ((user.name()))!", data={"user": {"name": simple_templating}}, result="Hello, John!")
def test_simpukka(text, data, filter_level, result):
    assert template.Template(text, data=data, filter_level=filter_level).start().result == result


@Parametrization.autodetect_parameters()
@Parametrization.default_parameters()
@Parametrization.case(name="Basic search test", text="hello ((user.name))", result=["user"])
@Parametrization.case(name="Empty scan", text="", result=[])
@Parametrization.case(name="No variables", text="Hello world", result=[])
@Parametrization.case(name="Inside ", text="(% if user %) (% endif %)", result=["user"])
def test_scan_root(text, result):
    assert template.analyse_variables(text).root == result
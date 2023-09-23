from parametrization import Parametrization

from simpukka import filters


@Parametrization.autodetect_parameters()
@Parametrization.default_parameters(whitelist=None)
@Parametrization.case(name="no_url", text="hello", replace_url="", expected="hello")
@Parametrization.case(name="no_url_replace", text="hello", replace_url="https://example.com/", expected="hello")
@Parametrization.case(name="only_url", text="https://google.com/", replace_url="", expected="")
@Parametrization.case(name="only_url_replace", text="https://google.com/", replace_url="https://example.com/", expected="https://example.com/")
@Parametrization.case(name="multiple_urls", text="https://google.com/ https://bing.com/", replace_url="", expected=" ")
@Parametrization.case(name="multiple_urls_in_text", text="Please visit this [site](https://google.com/) or https://bing.com/", replace_url="", expected="Please visit this [site]() or ")
@Parametrization.case(name="urls_whitelist", text="Please visit this [site](https://google.com/) or https://bing.com/", replace_url="", expected="Please visit this [site]() or https://bing.com/", whitelist=["bing.com"])
def test_url_filter(text, replace_url, expected, whitelist):
    if whitelist is None:
        whitelist = []
    assert filters.url_filter(text, replace_url=replace_url, whitelist=whitelist) == expected
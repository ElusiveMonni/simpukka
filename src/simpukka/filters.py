from urlextract import URLExtract

from simpukka import config

def url_filter(text: str, replace_url: str = config.replace_url, whitelist=config.whitelisted_domains, disabled=config.disable_url_filter):
    """Function which removes urls from provided string"""
    if disabled:
        return text
    extractor = URLExtract(allow_mixed_case_hostname=True, extract_email=True)
    extractor.ignore_list = whitelist
    for url in extractor.gen_urls(text):
        text = text.replace(url, replace_url, 1)
    return text

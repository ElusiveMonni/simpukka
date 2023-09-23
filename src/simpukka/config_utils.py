

def parse_list(text: str):
    """Function which parses list from ini file"""
    parsed = text.replace(" ", "").replace("\n", "").split(",")

    # List has only empty string then return empty list instead.
    return [] if parsed[0] == "" else parsed

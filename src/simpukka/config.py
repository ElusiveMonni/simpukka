import configparser
from simpukka.config_utils import parse_list


config = configparser.ConfigParser()

# Read configuration file
config.read('simpukka.ini')

# Save config values to memory.

# Filter section
disable_url_filter = config.getboolean("filter", "disable_url_filter", fallback=True)
whitelisted_domains = parse_list(config.get("filter", "whitelisted_domains", fallback=""))

replace_url = config.get("filter", "replace_url", fallback="")

# Template processor

timeout = config.getfloat("template", "timeout", fallback=5)

memory_limit = config.getfloat("template", "memory_limit", fallback=50)


block_start_string = config.get("template", "block_start_string", fallback="{%")

block_end_string = config.get("template", "block_end_string", fallback="%}")

variable_start_string = config.get("template", "variable_start_string", fallback="{{")

variable_end_string = config.get("template", "variable_end_string", fallback="}}")

line_statement_prefix = config.get("template", "line_statement_prefix", fallback="#")

line_comment_prefix = config.get("template", "line_comment_prefix", fallback="##")

python_interpreter = config.get("runtime", "python_interpreter", fallback=None)
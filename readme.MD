# Simpukka

Simpukka is template engine which builds upon jinja2 by adding sandbox and plugin system.

## Installation

`pip install git+https://github.com/ElusiveMonni/simpukka.git`


## Usage

```py
from simpukka import template

t = template.Template("String to render", data={})
r = t.start()

print("Result", r.content)

```



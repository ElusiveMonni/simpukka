import asyncio
import time
from enum import Enum
from importlib.metadata import entry_points
from attrs import define, field

import jinja2.utils
from jinja2.sandbox import SandboxedEnvironment, Environment, Context
from jinja2 import Undefined, meta
from jinja2.runtime import Undefined, UndefinedError

import simpukka.initialise
from simpukka import filters
from simpukka import config

import ray
from ray import exceptions as ray_exceptions

class RenderError(Exception):
    pass


class RenderMemoryExceeded(RenderError):
    """Happens when memory limit is exceeded."""
    pass


class RenderTimeoutError(RenderError):
    pass


@define
class SimpukkaPreScan:
    root: list


@define(frozen=False, hash=False, slots=False)
class Result:
    result: str
    time_taken: float
    error: RenderError = None
    api_calls: int = 0
    plugin_results: dict = {}
    shared: dict = None

class FilterLevel(Enum):
    """
    Levels of filtering for template. Strict always has all filters enabled.
    """
    disabled = 0
    moderate = 1
    strict = 2


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        print("UNDEFINED ERROR", self._undefined_name)
        return f'<!{self._undefined_name}!>'


def load_plugins(disabled, reverse_mode=False, **kwargs):
    data = {}
    shared = {}
    plugins = []
    for plugin in entry_points().select(group="simpukka.plugin"):
        if not reverse_mode and plugin.name in disabled or reverse_mode and plugin.name not in disabled :
            continue
        plugin = plugin.load()(**kwargs)
        plugin.pre_hook()
        plugins.append(plugin)
        p_data = plugin.data if hasattr(plugin, 'data') else plugin.get("data", {})
        data = data | p_data
        shared = shared | plugin.shared_data if hasattr(plugin, 'shared_data') else plugin.get("shared_data", {})

    return data, shared, plugins



class TrackedSandboxedEnvironment(SandboxedEnvironment):
    pass

    def getitem(self, obj, argument):
        print("Tracked get item", argument)
        r = super().getitem(obj, argument)
        print("Tracked get item result", r, argument)
        if argument == Undefined:
            print("MISSING")
        return r

@ray.remote(num_cpus=1, memory=20000000, max_retries=0)
def template_process(data, template_str, shared):
    env = TrackedSandboxedEnvironment(block_start_string=config.block_start_string,
                                      block_end_string=config.block_end_string,
                                      variable_start_string=config.variable_start_string,
                                      variable_end_string=config.variable_end_string,
                                      line_statement_prefix=config.line_statement_prefix,
                                      line_comment_prefix=config.line_comment_prefix
                                      )
    try:
        template = env.from_string(template_str)
        return template.render(**data, **shared), shared, 1
    except (UndefinedError, Exception) as e:
        return e, shared, 0



class TemplateProcess:
    """Class which handles the sandbox of template process."""

    def __init__(self, template: str, data: dict, shared_data: dict):
        """
        :param str template: String to render.
        :param dict data: Dictionary of external data to be passed to template.
        """
        self.data = data
        if data is None:
            self.data = {}

        self.shared_data = shared_data
        if shared_data is None:
            self.shared_data = {}

        self.template_str = template

    def run(self):
        error = ""
        result = "Failed to render!"
        start = time.time()
        shared = {}
        t = template_process.remote(self.data, self.template_str, shared=self.shared_data)
        try:
            r, shared, r_type = ray.get(t, timeout=config.timeout)
            if r_type:
                result = r
            else:
                error = r
        except ray_exceptions.GetTimeoutError:
            error = "timeout"
        return Result(result=result, time_taken=time.time()-start, error=error, shared=shared)

    async def run_async(self):
        error = ""
        result = "Failed to render!"
        start = time.time()
        shared = {}
        try:
            r, shared, r_type = await asyncio.wait_for(template_process.remote(self.data, self.template_str, shared=self.shared_data), timeout=config.timeout)
            if r_type:
                result = r
            else:
                error = r
        except asyncio.exceptions.TimeoutError:
            error = "timeout"
        return Result(result=result, time_taken=time.time()-start, error=error, shared=shared)


class Template:
    """
    Main class which handles loading everything needed for the template process
    """

    def __init__(self, string: str, filter_level: FilterLevel = FilterLevel.moderate, disabled_plugins = None, reverse_disable=False, data: dict = None, shared_data: dict = None,**kwargs):

        self.data = data
        if data is None:
            self.data = {}

        self.shared_data = shared_data
        if shared_data is None:
            self.shared_data = {}

        if disabled_plugins is None:
            disabled_plugins = []

        plugin_data, plugin_shared, plugins = load_plugins(disabled_plugins, reverse_disable, **kwargs)
        self.plugins = plugins
        self.data = plugin_data | self.data
        self.shared_data |= plugin_shared
        self.filter_level = filter_level
        self.string = string

    def start(self):
        r = TemplateProcess(self.string, data=self.data, shared_data=self.shared_data).run()

        if self.filter_level == FilterLevel.moderate:
            r.result = filters.url_filter(r.result)
        if self.filter_level == FilterLevel.strict:
            r.result = filters.url_filter(r.result)

        for p in self.plugins:
            p.after_hook(r)
        return r

    async def async_start(self):
        t = TemplateProcess(self.string, data=self.data, shared_data=self.shared_data)

        r = await t.run_async()

        if self.filter_level == FilterLevel.moderate:
            r.result = filters.url_filter(r.result)
        if self.filter_level == FilterLevel.strict:
            r.result = filters.url_filter(r.result)

        for p in self.plugins:
            await p.async_after_hook(r)
        return r


if __name__ == "__main__":
    simpukka.initialise.init_simpukka()
    #start = time.time()
    t = Template("Hello", filter_level=FilterLevel.moderate,
                 data={"applicant": {"name": "John", "age": 36, "Do you like cookies": "yes"}})
    r = t.start()
    print(r)
    t = Template("Hello {{applicant.name}}. Why do are you {{applicant.age}} years of age?", filter_level=FilterLevel.moderate,
                 data={"applicant": {"name": "John", "age": 36, "Do you like cookies": "yes"}})
    print(t.start())
    #end = time.time()
    #print("Whole time:", end-start, "s")
    #print("Render time:", r.time_taken, "s")
    #print("Outside render time:", end-start-r.time_taken, "s")
    #print("Ram usage:", r.peak_ram / 1024 ** 2, "mb")

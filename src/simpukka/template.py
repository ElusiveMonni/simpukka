import asyncio
import multiprocessing as mp
import time
from enum import Enum
from importlib.metadata import entry_points
from attrs import define, field

import jinja2.utils
from jinja2.sandbox import SandboxedEnvironment, Environment, Context
from jinja2 import Undefined, meta
from jinja2.runtime import Undefined, UndefinedError
from jinja2 import nodes
import psutil

from simpukka import filters
from simpukka import config

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
    peak_ram: float|int = 1
    error: RenderError = None
    api_calls: int = 0
    plugin_results: dict = {}

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
    plugins = []
    for plugin in entry_points().select(group="simpukka.plugin"):
        if not reverse_mode and plugin.name in disabled or reverse_mode and plugin.name not in disabled :
            continue
        plugin = plugin.load()(**kwargs)
        plugin.pre_hook()
        plugins.append(plugin)
        p_data = plugin.data if hasattr(plugin, 'data') else plugin.get("data", {})
        data = data | p_data
    return data, plugins



class TrackedSandboxedEnvironment(SandboxedEnvironment):
    pass

    def getitem(self, obj, argument):
        print("Tracked get item", argument)
        r = super().getitem(obj, argument)
        print("Tracked get item result", r, argument)
        if argument == Undefined:
            print("MISSING")
        return r

def template_process(data, result_dict, template_str):
    env = TrackedSandboxedEnvironment(block_start_string=config.block_start_string,
                                      block_end_string=config.block_end_string,
                                      variable_start_string=config.variable_start_string,
                                      variable_end_string=config.variable_end_string,
                                      line_statement_prefix=config.line_statement_prefix,
                                      line_comment_prefix=config.line_comment_prefix
                                      )
    try:
        template = env.from_string(template_str)
        result = template.render(**data)
        result_dict["result"] = result
    except (UndefinedError, Exception) as e:
        result_dict["error"] = e

class TemplateProcess:
    """Class which handles the sandbox of template process."""

    def __init__(self, template: str, data: dict):
        """
        :param str template: String to render.
        :param dict data: Dictionary of external data to be passed to template.
        """
        self.data = data
        if data is None:
            self.data = {}

        self.template_str = template

    def run(self):

        manager = mp.Manager()
        result_dict = manager.dict()
        result_dict["result"] = ""
        ctx = mp.get_context('spawn')

        if config.python_interpreter is not None:
            ctx.set_executable(config.python_interpreter)

        p = ctx.Process(target=template_process, daemon=True, args=(self.data, result_dict, self.template_str))
        p.start()

        ram_use = 1

        proc = psutil.Process(p.pid)
        while time.time() - proc.create_time() <= config.timeout:
            try:
                ram_use = proc.memory_info().peak_wset
                if ram_use / 1024 ** 2 > config.memory_limit:
                    result_dict["error"] = RenderMemoryExceeded("Maximum memory usage exceeded!")
                    p.kill()
                    break
            except psutil.NoSuchProcess:
                break
            time.sleep(.01)
        else:
            p.kill()
            result_dict["error"] = RenderTimeoutError("Rendering timed out!")

        took = time.time() - proc.create_time()
        return Result(result=result_dict["result"], time_taken=took, peak_ram=ram_use, error=result_dict.get("error"))



class Template:
    """
    Main class which handles loading everything needed for the template process
    """

    def __init__(self, string: str, filter_level: FilterLevel = FilterLevel.moderate, disabled_plugins = None, reverse_disable=False, data: dict = None, **kwargs):

        self.data = data
        if data is None:
            self.data = {}

        if disabled_plugins is None:
            disabled_plugins = []

        plugin_data, plugins = load_plugins(disabled_plugins, reverse_disable, **kwargs)
        self.plugins = plugins
        self.data = plugin_data | self.data

        self.filter_level = filter_level
        self.string = string

    def start(self):
        r = TemplateProcess(self.string, data=self.data).run()

        if self.filter_level == FilterLevel.moderate:
            r.result = filters.url_filter(r.result)
        if self.filter_level == FilterLevel.strict:
            r.result = filters.url_filter(r.result)

        for p in self.plugins:
            p.after_hook(r)
        return r

    async def async_start(self):
        t = TemplateProcess(self.string, data=self.data)
        loop = asyncio.get_event_loop()

        r = await loop.run_in_executor(None, t.run)

        if self.filter_level == FilterLevel.moderate:
            r.result = filters.url_filter(r.result)
        if self.filter_level == FilterLevel.strict:
            r.result = filters.url_filter(r.result)

        for p in self.plugins:
            await p.async_after_hook(r)
        return r



if __name__ == "__main__":
    start = time.time()
    t = Template("", filter_level=FilterLevel.moderate,
                 data={"applicant": {"name": "John", "age": 36, "Do you like cookies": "yes"}})
    r = t.start()
    print(r)
    end = time.time()
    print("Whole time:", end-start, "s")
    print("Render time:", r.time_taken, "s")
    print("Outside render time:", end-start-r.time_taken, "s")
    print("Ram usage:", r.peak_ram / 1024 ** 2, "mb")

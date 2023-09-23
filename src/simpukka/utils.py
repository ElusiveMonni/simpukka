from importlib.metadata import entry_points
from abc import abstractmethod
from typing import Mapping

from simpukka.template import Result

def loaded_libraries():
    return {
        plugin.name: {"entrypoint": plugin.load()}
        for plugin in entry_points().select(group="simpukka.plugin")
    }


class SimpukkaPlugin:
    """Simpukka results class to subclass. return func isn't provided it defaults to return_data"""

    data: Mapping

    def __init__(self, data=None, pre_hook_func=None, after_hook_func=None, **kwargs):
        self.data: Mapping = data
        if self.data is None:
            self.data = {}

        self.after_hook_func = after_hook_func
        if self.after_hook_func is None:
            self.after_hook_func = self.after_hook

        self.pre_hook_func = pre_hook_func
        if self.pre_hook_func is None:
            self.pre_hook_func = self.pre_hook

        self.kwargs = kwargs

    @abstractmethod
    def pre_hook(self):
        """Function which is ran before tempalate is processed."""
        pass

    @abstractmethod
    def after_hook(self, result: Result) -> Result:
        """Function which is ran once template has been processed"""
        pass

    @abstractmethod
    def async_after_hook(self, result: Result) -> Result:
        """Function which is ran once template has been processed"""
        pass

if __name__ == "__main__":
    print(loaded_libraries())
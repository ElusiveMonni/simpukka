import ray
import pathlib
from simpukka import template


def init_simpukka():
    ray.init(runtime_env={"working_dir": pathlib.Path(__file__).parent,
                          "eager_install": True})

    # Work around for issue with first task taking long
    template.Template("Init task").start()

import ray
import pathlib
from simpukka import template


def init_simpukka(remote_cluster=None):
    if remote_cluster is None:
        ray.init(runtime_env={"working_dir": pathlib.Path(__file__).parent,
                          "eager_install": True})
    else:
        ray.init(remote_cluster)
    # Work around for issue with first task taking long
    template.Template("Init task").start()


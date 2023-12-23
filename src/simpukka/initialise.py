import ray
import pathlib
import os
from simpukka import template
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

load_dotenv()


def setup_tunnel():
    remote_user = os.getenv("ray_server_user")
    remote_password = os.getenv("ray_server_password")
    remote_host = os.getenv("ray_server_host")
    remote_port = 22
    local_host = '127.0.0.1'

    server = SSHTunnelForwarder(
        (remote_host, remote_port),
        ssh_username=remote_user,
        ssh_password=remote_password,
        remote_bind_address=("0.0.0.0", 10001),
        local_bind_address=(local_host, 10001),
    )

    server.start()


def init_simpukka(remote_cluster=None, tunnel_required=False):
    if remote_cluster == "local":
        ray.init(ignore_reinit_error=True)
    elif tunnel_required:
            setup_tunnel()
            ray.init("ray://127.0.0.1:10001")
    elif remote_cluster is None:
        ray.init(runtime_env={"working_dir": pathlib.Path(__file__).parent,
                          "eager_install": True})
    else:
        ray.init(remote_cluster)

    # Work around for issue with first task taking long
    template.Template("Init task").start()

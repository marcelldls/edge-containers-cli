import os
import webbrowser
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import ruamel.yaml as yaml
import typer

from .shell import (
    K8S_GRAYLOG_URL,
    K8S_HELM_REGISTRY,
    check_helm,
    check_ioc,
    check_kubectl,
    run_command,
)

ioc = typer.Typer()


@ioc.command()
def attach(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC to attach to"),
):
    """Attach to the IOC shell of a live IOC"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    run_command(
        f"kubectl -it -n {bl} attach  deploy/{ioc_name}",
        show=True,
        interactive=True,
    )


@ioc.command()
def delete(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC to delete"),
):
    """Remove an IOC helm deployment from the cluster"""

    check_helm(local=True)
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    if not typer.confirm(
        f"This will remove all versions of {ioc_name} "
        "from the cluster. Are you sure ?"
    ):
        raise typer.Abort()

    run_command(
        f"helm delete -n {bl} {ioc_name}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def deploy_local(
    ctx: typer.Context,
    ioc_path: Path = typer.Argument(
        ..., help="root folder of local helm chart to deploy"
    ),
):
    """Deploy a local IOC helm chart directly to the cluster with dated beta version"""

    version = datetime.strftime(datetime.now(), "%Y.%-m.%-d-b%-H.%-M")
    bl = ctx.obj.beamline
    check_helm(local=True)

    # verify this is a helm chart and extract the IOC name from it
    with open(ioc_path / "Chart.yaml", "r") as stream:
        chart = yaml.safe_load(stream)

    ioc_name = chart["name"]
    ioc_path = ioc_path.absolute()

    print(
        f"Deploy {ioc_name} TEMPORARY version {version} "
        f"from {ioc_path} to beamline {bl}"
    )
    if not typer.confirm("Are you sure ?"):
        raise typer.Abort()

    with TemporaryDirectory() as temp:
        os.chdir(temp)
        run_command(
            f"helm package -u {ioc_path} --version {version} --app-version {version}",
            show=True,
            show_cmd=ctx.obj.show_cmd,
        )
        package = list(Path(".").glob("*.tgz"))[0]
        run_command(
            f"helm upgrade --install {ioc_name} {package}",
            show=True,
            show_cmd=ctx.obj.show_cmd,
        )


@ioc.command()
def deploy(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC to deploy"),
    version: str = typer.Argument(..., help="Version tag of the IOC to deploy"),
    helm_registry: Optional[str] = typer.Option(
        K8S_HELM_REGISTRY, help="Helm registry to pull from"
    ),
):
    """Pull an IOC helm chart and deploy it to the cluster"""

    registry = check_helm(helm_registry)
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    run_command(
        f"helm upgrade -n {bl} --install {ioc_name} "
        f"oci://{registry}/{ioc_name} --version {version}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def exec(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC container to run in"),
):
    """Execute a bash prompt in a live IOC's container"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    run_command(
        f"kubectl -it -n {bl} exec  deploy/{ioc_name} -- bash",
        show=True,
        interactive=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def graylog(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(
        ...,
        help="Name of the IOC to inspect",
    ),
):
    """Open graylog historical logs for an IOC"""

    if K8S_GRAYLOG_URL is None:
        print("K8S_GRAYLOG_URL environment not set")
        raise typer.Exit(1)

    webbrowser.open(
        f"{K8S_GRAYLOG_URL}/search?rangetype=relative&fields=message%2Csource"
        f"&width=1489&highlightMessage=&relative=172800&q=pod_name%3A{ioc_name}*"
    )


@ioc.command()
def logs(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC to inspect"),
    prev: bool = typer.Option(
        False, "--previous", "-p", help="Show log from the previous instance of the IOC"
    ),
):
    """Show logs for current and previous instances of an IOC"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    previous = "-p" if prev else ""

    run_command(
        f"kubectl -n {bl} logs deploy/{ioc_name} {previous}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def restart(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC container to restart"),
):
    """Restart an IOC"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    podname = run_command(f"kubectl get -n {bl} pod -l app={ioc_name} -o name")
    run_command(
        f"kubectl delete -n {bl} {podname}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def start(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC container to start"),
):
    """Start an IOC"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    run_command(
        f"kubectl scale -n {bl} deploy --replicas=1 {ioc_name}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def stop(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC container to stop"),
):
    """Stop an IOC"""

    check_kubectl()
    bl = ctx.obj.beamline
    check_ioc(ioc_name, bl)

    run_command(
        f"kubectl scale -n {bl} deploy --replicas=0 {ioc_name}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )


@ioc.command()
def versions(
    ctx: typer.Context,
    ioc_name: str = typer.Argument(..., help="Name of the IOC to inspect"),
    helm_registry: Optional[str] = typer.Option(
        K8S_HELM_REGISTRY, help="Helm registry to pull from"
    ),
):
    """List all versions of the IOC available in the helm registry"""

    registry = check_helm(helm_registry)

    run_command(
        f"podman run --rm quay.io/skopeo/stable "
        f"list-tags docker://{registry}/{ioc_name}",
        show=True,
        show_cmd=ctx.obj.show_cmd,
    )
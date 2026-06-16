"""Typer command-line interface for GTEx-Link.

GeneFoundry Logging & CLI Standard v1: a single ``Typer`` app exposing
``serve`` / ``config`` / ``health`` / ``cache`` / ``version``. Streamable HTTP
only — there is no stdio transport and no bare-serve entry point. The server
boots via ``gtex-link serve`` in either the ``unified`` (FastAPI REST + MCP at
``/mcp``) or ``http`` (FastAPI only) transport.
"""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING, Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import get_api_config, get_cache_config, settings
from .logging_config import configure_logging
from .server_manager import UnifiedServerManager

if TYPE_CHECKING:
    from types import FrameType

app = typer.Typer(
    name="gtex-link",
    add_completion=False,
    no_args_is_help=True,
    help="gtex-link: an MCP/API server grounding expression research in GTEx Portal.",
)
cache_app = typer.Typer(
    name="cache",
    add_completion=False,
    no_args_is_help=True,
    help="Inspect or clear the in-process service cache.",
)
app.add_typer(cache_app, name="cache")
console = Console()


async def _serve(host: str, port: int, *, unified: bool) -> None:
    """Run the unified or HTTP-only server until interrupted."""
    logger = configure_logging()
    manager = UnifiedServerManager(logger=logger)

    shutdown_task: asyncio.Task[None] | None = None

    def _signal(signum: int, _frame: FrameType | None) -> None:
        nonlocal shutdown_task
        logger.info("Received shutdown signal", signal=signum)
        if shutdown_task is None or shutdown_task.done():
            shutdown_task = asyncio.create_task(manager.shutdown())

    signal.signal(signal.SIGINT, _signal)
    # SIGTERM may not be deliverable on Windows; SIGINT (Ctrl-C) still works.
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal)

    try:
        if unified:
            await manager.start_unified_server(host=host, port=port)
        else:
            await manager.start_http_only_server(host=host, port=port)
    finally:
        await manager.shutdown()


@app.command()
def serve(
    transport: Annotated[
        str,
        typer.Option("--transport", help="Transport mode: 'unified' (REST + MCP/HTTP) or 'http'."),
    ] = "unified",
    host: Annotated[str, typer.Option("--host", help="Host to bind to.")] = settings.host,
    port: Annotated[int, typer.Option("--port", help="Port to bind to.")] = settings.port,
    mcp_path: Annotated[
        str, typer.Option("--mcp-path", help="MCP endpoint path.")
    ] = settings.mcp_path,
    log_level: Annotated[
        str, typer.Option("--log-level", help="Logging level.")
    ] = settings.log_level,
    disable_docs: Annotated[
        bool, typer.Option("--disable-docs", help="Disable API documentation endpoints.")
    ] = False,
    dev: Annotated[
        bool, typer.Option("--dev", help="Development mode (verbose console logging).")
    ] = False,
) -> None:
    """Start the gtex-link server (Streamable HTTP only)."""
    if transport not in ("unified", "http"):
        console.print(
            f"[red]Invalid transport '{transport}'.[/red] Choose 'unified' or 'http' "
            "(stdio is not supported)."
        )
        raise typer.Exit(code=2)

    settings.transport = transport  # type: ignore[assignment]
    settings.host = host
    settings.port = port
    settings.mcp_path = mcp_path
    settings.log_level = "DEBUG" if dev else log_level  # type: ignore[assignment]
    settings.disable_docs = disable_docs
    settings.reload = dev

    console.print(
        f"[green]Starting gtex-link[/green] transport={transport} "
        f"host={host} port={port} mcp_path={mcp_path}"
    )
    asyncio.run(_serve(host, port, unified=transport == "unified"))


@app.command()
def config(
    validate: Annotated[
        bool, typer.Option("--validate", help="Validate the resolved configuration.")
    ] = False,
) -> None:
    """Show (and optionally validate) the resolved configuration."""
    api_config = get_api_config()
    cache_config = get_cache_config()

    server_table = Table(title="gtex-link configuration")
    server_table.add_column("Setting", style="cyan")
    server_table.add_column("Value", style="white")
    server_table.add_row("transport", settings.transport)
    server_table.add_row("host", settings.host)
    server_table.add_row("port", str(settings.port))
    server_table.add_row("mcp_path", settings.mcp_path)
    server_table.add_row("log_level", settings.log_level)
    server_table.add_row("log_format", settings.log_format)
    server_table.add_row("api.base_url", api_config.base_url)
    server_table.add_row("api.timeout", f"{api_config.timeout}s")
    server_table.add_row("cache.size", str(cache_config.size))
    server_table.add_row("cache.ttl", f"{cache_config.ttl}s")
    console.print(server_table)

    if validate:
        if not 1024 <= settings.port <= 65535:
            console.print("[red]Invalid port number[/red]")
            raise typer.Exit(code=1)
        if not settings.mcp_path.startswith("/"):
            console.print("[red]MCP path must start with '/'[/red]")
            raise typer.Exit(code=1)
        console.print("[green]Configuration is valid[/green]")


@app.command()
def health(
    url: Annotated[
        str, typer.Option("--url", help="Base URL of the server to probe.")
    ] = "http://127.0.0.1:8000",
) -> None:
    """Check a running server's /api/health endpoint."""
    try:
        response = httpx.get(f"{url.rstrip('/')}/api/health", timeout=5)
    except httpx.HTTPError as exc:
        console.print(f"[red]Failed to connect to server:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if response.status_code != 200:
        console.print(f"[red]Server returned status {response.status_code}[/red]")
        raise typer.Exit(code=1)

    data = response.json()
    console.print("[green]Server is healthy[/green]")
    console.print(f"status:  {data.get('status', 'unknown')}")
    console.print(f"version: {data.get('version', 'unknown')}")
    console.print(f"gtex_api: {data.get('gtex_api', 'unknown')}")


def _build_service() -> object:
    """Construct a GTExService bound to a fresh client for cache inspection."""
    from .api.client import GTExClient
    from .services.gtex_service import GTExService

    logger = configure_logging()
    client = GTExClient(config=get_api_config(), logger=logger)
    return GTExService(client, get_cache_config(), logger)


@cache_app.command("stats")
def cache_stats() -> None:
    """Show in-process cache statistics."""
    service = _build_service()
    stats = service.cache_stats  # type: ignore[attr-defined]
    info = service.get_cache_info()  # type: ignore[attr-defined]

    table = Table(title="gtex-link cache statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("hits", str(stats.get("hits", 0)))
    table.add_row("misses", str(stats.get("misses", 0)))
    table.add_row("hit_rate", f"{stats.get('hit_rate', 0.0):.1f}%")
    table.add_row("total_requests", str(stats.get("total_requests", 0)))
    table.add_row("cached_functions", str(stats.get("cached_functions", 0)))
    console.print(table)
    console.print(f"tracked cache surfaces: {len(info)}")


@cache_app.command("clear")
def cache_clear() -> None:
    """Clear all in-process caches and reset counters."""
    service = _build_service()
    result = service.clear_cache()  # type: ignore[attr-defined]
    console.print(
        f"[green]Cleared caches[/green] (cleared_functions={result.get('cleared_functions', 0)})"
    )


@app.command()
def version() -> None:
    """Print the installed gtex-link version."""
    console.print(f"gtex-link {__version__}")


if __name__ == "__main__":
    app()

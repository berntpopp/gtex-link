"""Command-line interface for GTEx-Link."""

from __future__ import annotations

import argparse
import asyncio
import sys

from fastapi import HTTPException
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import get_api_config, get_cache_config
from .logging_config import configure_logging
from .server_manager import UnifiedServerManager

# Initialize rich console
console = Console()


async def test_connection() -> bool:
    """Test connection to GTEx Portal API."""
    logger = configure_logging()

    with console.status("[bold blue]Testing GTEx Portal API connection...", spinner="dots"):
        try:
            # Import here to avoid circular imports
            from .api.client import GTExClient

            config = get_api_config()
            async with GTExClient(config=config, logger=logger) as client:
                # Test with service info endpoint
                result = await client.get_service_info()

                if result:
                    console.print(
                        Panel(
                            (
                                "[bold green]:white_check_mark: "
                                "Successfully connected to GTEx Portal API\n"
                                "Service info retrieved successfully"
                            ),
                            title="Connection Test",
                            border_style="green",
                        ),
                    )
                    return True
                console.print(
                    Panel(
                        "[bold yellow]:warning: Connected but no service info returned",
                        title="Connection Test",
                        border_style="yellow",
                    ),
                )
                return True

        except (HTTPException, ConnectionError, TimeoutError) as e:
            console.print(
                Panel(
                    f"[bold red]:x: Connection failed: {e!s}",
                    title="Connection Test",
                    border_style="red",
                ),
            )
            return False


async def search_genes(query: str, limit: int = 10) -> None:
    """Search for genes."""
    logger = configure_logging()

    search_desc = f"[bold blue]Searching for genes: '{query}'"

    with console.status(search_desc, spinner="dots"):
        try:
            # Import here to avoid circular imports
            from .api.client import GTExClient
            from .services.gtex_service import GTExService

            config = get_api_config()
            async with GTExClient(config=config, logger=logger) as client:
                service = GTExService(client, get_cache_config(), logger)
                result = await service.search_genes(query=query, page_size=limit)

                # Create a table for results
                table = Table(title=f"Gene Search Results for '{query}'")
                table.add_column("Gene Symbol", style="cyan", no_wrap=True)
                table.add_column("Gene Name", style="green")
                table.add_column("Chromosome", style="magenta")
                table.add_column("Start", style="yellow", justify="right")
                table.add_column("End", style="yellow", justify="right")
                table.add_column("Strand", style="blue")

                if hasattr(result, "data") and result.data:
                    for gene in result.data[:limit]:
                        table.add_row(
                            gene.gene_symbol or "N/A",
                            gene.description or "N/A",
                            str(gene.chromosome) if gene.chromosome else "N/A",
                            str(gene.start) if hasattr(gene, "start") and gene.start else "N/A",
                            str(gene.end) if hasattr(gene, "end") and gene.end else "N/A",
                            str(gene.strand) if hasattr(gene, "strand") and gene.strand else "N/A",
                        )

                    console.print(table)
                    console.print(f"\n[bold green]Found {len(result.data)} gene(s)")
                else:
                    console.print(f"[bold yellow]No genes found for query: '{query}'")

        except (HTTPException, ConnectionError, TimeoutError) as e:
            console.print(
                Panel(
                    f"[bold red]:x: Search failed: {e!s}",
                    title="Gene Search Error",
                    border_style="red",
                ),
            )


def show_config() -> None:
    """Display current configuration."""
    config = get_api_config()
    cache_config = get_cache_config()

    # API Configuration Table
    api_table = Table(title="GTEx Portal API Configuration")
    api_table.add_column("Setting", style="cyan")
    api_table.add_column("Value", style="green")

    api_table.add_row("Base URL", config.base_url)
    api_table.add_row("Timeout", f"{config.timeout}s")
    api_table.add_row("Rate Limit", f"{config.rate_limit_per_second}/s")
    api_table.add_row("Burst Size", str(config.burst_size))
    api_table.add_row("Max Retries", str(config.max_retries))
    api_table.add_row("Retry Delay", f"{config.retry_delay}s")
    api_table.add_row("User Agent", config.user_agent)

    # Cache Configuration Table
    cache_table = Table(title="Cache Configuration")
    cache_table.add_column("Setting", style="cyan")
    cache_table.add_column("Value", style="green")

    cache_table.add_row("Size", str(cache_config.size))
    cache_table.add_row("TTL", f"{cache_config.ttl}s")
    cache_table.add_row("Stats Enabled", str(cache_config.stats_enabled))
    cache_table.add_row("Cleanup Interval", f"{cache_config.cleanup_interval}s")

    console.print(api_table)
    console.print()
    console.print(cache_table)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="GTEx-Link: High-performance MCP/API server for GTEx Portal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the server")
    server_parser.add_argument(
        "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)"
    )
    server_parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    server_parser.add_argument(
        "--mode",
        choices=["http", "stdio", "unified"],
        default="unified",
        help="Server mode (default: unified)",
    )
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Test command
    subparsers.add_parser("test", help="Test API connection")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for genes")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum results (default: 10)"
    )

    # Config command
    subparsers.add_parser("config", help="Show configuration")

    return parser


async def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    mode: str = "unified",
    *,
    reload: bool = False,
) -> None:
    """Run the server."""
    logger = configure_logging()
    server_manager = UnifiedServerManager(logger=logger)

    try:
        await server_manager.start_server(host=host, port=port, mode=mode, reload=reload)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Server stopped by user")
    except (OSError, RuntimeError) as e:
        console.print(
            Panel(
                f"[bold red]:x: Server failed to start: {e!s}",
                title="Server Error",
                border_style="red",
            ),
        )
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "server":
            asyncio.run(
                run_server(
                    host=args.host,
                    port=args.port,
                    mode=args.mode,
                    reload=args.reload,
                )
            )
        elif args.command == "test":
            success = asyncio.run(test_connection())
            sys.exit(0 if success else 1)
        elif args.command == "search":
            asyncio.run(search_genes(args.query, args.limit))
        elif args.command == "config":
            show_config()
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user")
        sys.exit(1)
    except (ValueError, RuntimeError, OSError) as e:
        console.print(
            Panel(
                f"[bold red]:x: Command failed: {e!s}",
                title="Error",
                border_style="red",
            ),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

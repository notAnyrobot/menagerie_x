"""Browser-based workbench backed by the menagerie asset catalog."""

from .server import create_server, main

__all__ = ["create_server", "main"]

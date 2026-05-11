"""`python -m gtex_link` entry — aliases `server.py --transport unified`."""

from __future__ import annotations

# `server.py` is a script at the project root; it is on sys.path because
# the project root is the runtime cwd when invoked as `python -m gtex_link`.
from server import main

if __name__ == "__main__":
    main()

"""Entry point: ``python -m gns3presence``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

"""Entry point used to build the standalone executable.

PyInstaller needs a script that does *absolute* imports: the relative imports
of ``gns3presence/__main__.py`` do not work once frozen.

Usage::

    pyinstaller --onefile --name gns3-presence --collect-all pypresence entrypoint.py
"""

import sys

from gns3presence.cli import main

if __name__ == "__main__":
    sys.exit(main())

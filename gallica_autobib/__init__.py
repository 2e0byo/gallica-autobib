from importlib.metadata import version

import coloredlogs

__version__ = version(__name__)

coloredlogs.install()

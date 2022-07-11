from importlib.metadata import version
from typing import Iterable, Union

import coloredlogs

__version__ = version(__name__)

coloredlogs.install()


def as_string(x: Union[str, Iterable]):
    """Convert something to a string."""
    if isinstance(x, str):
        return x
    else:
        return " ".join(x)

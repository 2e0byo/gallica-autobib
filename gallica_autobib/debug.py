try:
    from devtools import debug
except ImportError:

    def debug(*args, **kwargs):
        """Silently hide."""

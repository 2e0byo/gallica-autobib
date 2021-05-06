def assemble_query(**kwargs) -> str:
    """Put together an sru query from a dict."""
    return " and ".join(f'{k} all "{v}"' for k, v in kwargs.items())

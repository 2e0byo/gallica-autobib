from jinja2 import Environment, PackageLoader, select_autoescape

latex_env = Environment(
    block_start_string="\\BLOCK{",
    block_end_string="}",
    variable_start_string="\\VAR{",
    variable_end_string="}",
    comment_start_string="\\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    autoescape=False,
    loader=PackageLoader("gallica_autobib", "templates"),
)

env = Environment(
    loader=PackageLoader("gallica_autobib", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

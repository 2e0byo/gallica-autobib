from typing import Any, Union

from lark import Transformer

from .monadic import Left, Right

class Ark:
    def __init__(self, **ark_parts: Any) -> None: ...
    def copy(self) -> Ark: ...
    @property
    def scheme(self) -> str: ...
    @property
    def authority(self) -> str: ...
    @property
    def naan(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def qualifier(self) -> str: ...
    @property
    def arkid(self) -> str: ...
    @property
    def root(self) -> str: ...
    @property
    def parts(self) -> dict: ...
    def is_arkid(self) -> bool: ...
    @staticmethod
    def parse(ark_str: Any) -> Union[Left, Right]: ...

class ArkParsingError(ValueError):
    def __init__(self, message: Any, arkstr: Any) -> None: ...

class ArkIdTransformer(Transformer):
    @staticmethod
    def naan(item: Any) -> str: ...
    @staticmethod
    def name(item: Any) -> str: ...
    @staticmethod
    def qualifier(item: Any) -> str: ...
    @staticmethod
    def arkid(items: Any) -> str: ...

from typing import Any, Optional

from .ark import Ark as Ark
from .monadic import Future as Future, Left as Left

class Resource:
    timeout: int = ...
    def __init__(self, ark: Any) -> None: ...
    @property
    def ark(self) -> Any: ...
    @property
    def arkid(self) -> Any: ...
    def issues(self, year: str = ...) -> Any: ...
    def oairecord(self) -> Any: ...
    def pagination(self) -> Any: ...
    def image_preview(self, resolution: str = ..., view: int = ...) -> Any: ...
    def fulltext_search(
        self, query: str = ..., view: int = ..., results_per_set: int = ...
    ) -> Any: ...
    def toc(self) -> Any: ...
    def content(
        self,
        startview: Optional[Any] = ...,
        nviews: Optional[Any] = ...,
        mode: str = ...,
    ) -> Any: ...
    def ocr_data(self, view: Any) -> Any: ...
    def iiif_info(self, view: str = ...) -> Any: ...
    def iiif_data(
        self,
        view: str = ...,
        region: Optional[Any] = ...,
        size: str = ...,
        rotation: int = ...,
        quality: str = ...,
        imformat: str = ...,
    ) -> Any: ...
    def oairecord_sync(self) -> Any: ...
    def issues_sync(self, year: str = ...) -> Any: ...
    def pagination_sync(self) -> Any: ...
    def image_preview_sync(self, resolution: str = ..., view: int = ...) -> Any: ...
    def fulltext_search_sync(
        self, query: Any, view: int = ..., results_per_set: int = ...
    ) -> Any: ...
    def toc_sync(self) -> Any: ...
    def content_sync(
        self,
        startview: int = ...,
        nviews: Optional[Any] = ...,
        mode: str = ...,
        url_only: bool = ...,
    ) -> Any: ...
    def ocr_data_sync(self, view: Any) -> Any: ...
    def iiif_info_sync(self, view: int = ...) -> Any: ...
    def iiif_data_sync(
        self,
        view: int = ...,
        region: Optional[Any] = ...,
        size: str = ...,
        rotation: int = ...,
        quality: str = ...,
        imformat: str = ...,
    ) -> Any: ...

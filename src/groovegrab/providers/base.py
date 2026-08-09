"""
Abstract Base Provider Protocol
"""

from abc import ABC, abstractmethod
from typing import List, Union
from groovegrab.core.models import TrackInfo, PlaylistInfo


class BaseProvider(ABC):
    """Abstract Base Class for all GrooveGrab extractors/providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @abstractmethod
    def can_handle(self, query_or_url: str) -> bool:
        """Determines if this provider can handle the given URL or search query."""
        pass

    @abstractmethod
    def resolve(self, query_or_url: str) -> Union[TrackInfo, PlaylistInfo]:
        """Resolves metadata and stream information from URL or query."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[TrackInfo]:
        """Performs search on provider platform."""
        pass

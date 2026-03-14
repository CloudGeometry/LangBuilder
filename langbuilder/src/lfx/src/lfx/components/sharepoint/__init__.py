"""SharePoint Components Bundle

Provides a suite of components for integrating with Microsoft SharePoint.
Includes authentication, file retrieval, and list item querying capabilities.

Components:
- SharePointAuth: Authenticates with SharePoint using OAuth 2.0
- SharePointGetFile: Retrieves files from SharePoint document libraries
- SharePointListItems: Queries items from SharePoint lists
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sharepoint_auth import SharePointAuth
    from .sharepoint_get_file import SharePointGetFile
    from .sharepoint_list_items import SharePointListItems


def __getattr__(name: str):
    """Lazy loading of SharePoint components."""
    if name == "SharePointAuth":
        from .sharepoint_auth import SharePointAuth
        return SharePointAuth
    if name == "SharePointGetFile":
        from .sharepoint_get_file import SharePointGetFile
        return SharePointGetFile
    if name == "SharePointListItems":
        from .sharepoint_list_items import SharePointListItems
        return SharePointListItems
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SharePointAuth",
    "SharePointGetFile",
    "SharePointListItems",
]

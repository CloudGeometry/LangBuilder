"""HubSpot components for LangBuilder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lfx.components._importing import import_mod

if TYPE_CHECKING:
    from .hubspot_company_fetcher import HubSpotCompanyFetcher
    from .hubspot_contact_creator import HubSpotContactCreatorComponent
    from .hubspot_contact_fetcher import HubSpotContactFetcher
    from .hubspot_contact_search import HubSpotContactSearchComponent
    from .hubspot_contact_updater import HubSpotContactUpdater
    from .hubspot_context_gather import HubSpotContextGatherComponent
    from .hubspot_file_uploader import HubSpotFileUploader
    from .hubspot_note_creator import HubSpotNoteCreator
    from .hubspot_property_update import HubSpotPropertyUpdateComponent

_dynamic_imports = {
    "HubSpotCompanyFetcher": "hubspot_company_fetcher",
    "HubSpotContactCreatorComponent": "hubspot_contact_creator",
    "HubSpotContactFetcher": "hubspot_contact_fetcher",
    "HubSpotContactSearchComponent": "hubspot_contact_search",
    "HubSpotContactUpdater": "hubspot_contact_updater",
    "HubSpotContextGatherComponent": "hubspot_context_gather",
    "HubSpotFileUploader": "hubspot_file_uploader",
    "HubSpotNoteCreator": "hubspot_note_creator",
    "HubSpotPropertyUpdateComponent": "hubspot_property_update",
}

__all__ = [
    "HubSpotCompanyFetcher",
    "HubSpotContactCreatorComponent",
    "HubSpotContactFetcher",
    "HubSpotContactSearchComponent",
    "HubSpotContactUpdater",
    "HubSpotContextGatherComponent",
    "HubSpotFileUploader",
    "HubSpotNoteCreator",
    "HubSpotPropertyUpdateComponent",
]


def __getattr__(attr_name: str) -> Any:
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result
    return result


def __dir__() -> list[str]:
    return list(__all__)

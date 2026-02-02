from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langbuilder.components._importing import import_mod

if TYPE_CHECKING:
    from langbuilder.components.cloudgeometry.jinja2_renderer import Jinja2Renderer
    from langbuilder.components.cloudgeometry.contact_info_extractor import ContactInfoExtractorComponent
    from langbuilder.components.cloudgeometry.pinecone_search_tool import PineconeSearchToolComponent
    from langbuilder.components.cloudgeometry.pinecone_store_tool import PineconeStoreToolComponent
    from langbuilder.components.cloudgeometry.dummy_component import CloudGeometryDummyComponent
    from langbuilder.components.cloudgeometry.atlassian_mcp_component import AtlassianMCPComponent
    from langbuilder.components.cloudgeometry.action_plan_store import ActionPlanStoreComponent
    from langbuilder.components.cloudgeometry.slack_block_kit_poster import SlackBlockKitPosterComponent
    from langbuilder.components.cloudgeometry.slack_event_parser import SlackEventParserComponent
    from langbuilder.components.cloudgeometry.slack_dashboard_updater import SlackDashboardUpdaterComponent
    from langbuilder.components.cloudgeometry.per_user_jira_auth import PerUserJiraAuthComponent
    from langbuilder.components.cloudgeometry.slack_modal_trigger import SlackModalTriggerComponent
    from langbuilder.components.cloudgeometry.slack_component import SlackComponent

_dynamic_imports = {
    "Jinja2Renderer": "jinja2_renderer",
    "ContactInfoExtractorComponent": "contact_info_extractor",
    "PineconeSearchToolComponent": "pinecone_search_tool",
    "PineconeStoreToolComponent": "pinecone_store_tool",
    "CloudGeometryDummyComponent": "dummy_component",
    "AtlassianMCPComponent": "atlassian_mcp_component",
    "ActionPlanStoreComponent": "action_plan_store",
    "SlackBlockKitPosterComponent": "slack_block_kit_poster",
    "SlackEventParserComponent": "slack_event_parser",
    "SlackDashboardUpdaterComponent": "slack_dashboard_updater",
    "PerUserJiraAuthComponent": "per_user_jira_auth",
    "SlackModalTriggerComponent": "slack_modal_trigger",
    "SlackComponent": "slack_component",
}

__all__ = [
    "Jinja2Renderer",
    "ContactInfoExtractorComponent",
    "PineconeSearchToolComponent",
    "PineconeStoreToolComponent",
    "CloudGeometryDummyComponent",
    "AtlassianMCPComponent",
    "ActionPlanStoreComponent",
    "SlackBlockKitPosterComponent",
    "SlackEventParserComponent",
    "SlackDashboardUpdaterComponent",
    "PerUserJiraAuthComponent",
    "SlackModalTriggerComponent",
    "SlackComponent",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import CloudGeometry components on attribute access."""
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

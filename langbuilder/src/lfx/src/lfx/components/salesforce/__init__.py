from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .salesforce_auth import SalesforceAuthComponent
    from .salesforce_create_record import SalesforceCreateRecordComponent
    from .salesforce_get_record import SalesforceGetRecordComponent
    from .salesforce_query import SalesforceQueryComponent

__all__ = [
    "SalesforceAuthComponent",
    "SalesforceCreateRecordComponent",
    "SalesforceGetRecordComponent",
    "SalesforceQueryComponent",
]


def __getattr__(name: str):
    if name == "SalesforceAuthComponent":
        from .salesforce_auth import SalesforceAuthComponent

        return SalesforceAuthComponent
    if name == "SalesforceCreateRecordComponent":
        from .salesforce_create_record import SalesforceCreateRecordComponent

        return SalesforceCreateRecordComponent
    if name == "SalesforceGetRecordComponent":
        from .salesforce_get_record import SalesforceGetRecordComponent

        return SalesforceGetRecordComponent
    if name == "SalesforceQueryComponent":
        from .salesforce_query import SalesforceQueryComponent

        return SalesforceQueryComponent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

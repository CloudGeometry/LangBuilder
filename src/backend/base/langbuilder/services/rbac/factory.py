"""Factory for creating RBACService instances."""

from typing_extensions import override

from langbuilder.services.factory import ServiceFactory
from langbuilder.services.rbac.service import RBACService


class RBACServiceFactory(ServiceFactory):
    """Factory for creating RBACService instances."""

    name = "rbac_service"

    def __init__(self) -> None:
        super().__init__(RBACService)

    @override
    def create(self) -> RBACService:
        """Create a new RBACService instance."""
        return RBACService()

"""
CloudGeometry Dummy Component

A minimal, no-op component used to verify UI loading.
"""

from langflow.custom import Component
from langflow.io import Output, StrInput
from langflow.schema import Data


class CloudGeometryDummyComponent(Component):
    """Minimal component that returns a stub payload for UI visibility."""

    display_name = "CloudGeometry Dummy"
    description = "Test component used to verify UI loading."
    icon = "beaker"
    name = "CloudGeometryDummy"

    inputs = [
        StrInput(
            name="note",
            display_name="Note",
            required=False,
            value="",
            info="Optional note; component does not perform any action.",
        ),
    ]

    outputs = [
        Output(
            name="dummy",
            display_name="Dummy Output",
            method="build_dummy",
        ),
    ]

    def build_dummy(self) -> Data:
        """Return a stub payload; useful for UI testing only."""
        self.status = "Dummy component executed"
        return Data(data={"note": self.note or "", "ok": True})

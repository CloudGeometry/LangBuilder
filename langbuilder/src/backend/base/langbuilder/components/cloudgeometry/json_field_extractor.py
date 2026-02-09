"""
JSON Field Extractor - Custom LangBuilder Component

Takes a JSON string (e.g. from ChatInput) and extracts a single field by name.
Useful for pulling slack_id out of a scheduler payload before passing to DynamoDB.
"""

import json

from langbuilder.custom import Component
from langbuilder.io import MessageTextInput, Output
from langbuilder.schema.message import Message


class JSONFieldExtractor(Component):
    display_name = "JSON Field Extractor"
    description = "Extracts a single field from a JSON string input."
    icon = "braces"
    name = "JSONFieldExtractor"

    inputs = [
        MessageTextInput(
            name="input_value",
            display_name="JSON Input",
            info="JSON string to parse (e.g. from ChatInput).",
            required=True,
        ),
        MessageTextInput(
            name="field_name",
            display_name="Field Name",
            info="Name of the field to extract (e.g. slack_id).",
            value="slack_id",
            required=True,
        ),
    ]

    outputs = [
        Output(display_name="Value", name="extracted_value", method="extract"),
    ]

    def extract(self) -> Message:
        raw = self.input_value
        if hasattr(raw, "text"):
            raw = raw.text

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self.status = "Invalid JSON"
            return Message(text=str(raw).strip())

        field = self.field_name
        if hasattr(field, "text"):
            field = field.text

        value = data.get(field.strip(), "")
        self.status = f"{field}={value}"
        return Message(text=str(value))

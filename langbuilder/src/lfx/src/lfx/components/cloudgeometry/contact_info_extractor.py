"""
Contact Info Extractor - LangBuilder Custom Component

Parses natural language input to extract contact name/ID and topic.
Supports inputs like "Ken about AI Transformation" or "4364201 Cloud Migration".

Author: CloudGeometry
"""

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data
from langflow.logging import logger
import re


class ContactInfoExtractorComponent(Component):
    """
    Parse natural language input to extract contact identification and topic.

    Examples:
    - "Ken about AI Transformation" -> {contact_name: "Ken", topic: "AI Transformation"}
    - "John Smith about Kubernetes" -> {contact_name: "John Smith", topic: "Kubernetes"}
    - "4364201 AI Transformation" -> {contact_id: "4364201", topic: "AI Transformation"}
    - "generate email for Ken English about DevOps" -> {contact_name: "Ken English", topic: "DevOps"}

    This component is designed to work with the Email Copywriter flow,
    enabling natural language input instead of requiring a contact_id upfront.
    """

    display_name = "Contact Info Extractor"
    description = "Parse natural language to extract contact name/ID and topic"
    icon = "users"
    name = "ContactInfoExtractor"

    # Words to strip from the beginning/around names
    FILLER_WORDS = [
        "generate",
        "create",
        "draft",
        "write",
        "send",
        "make",
        "email",
        "message",
        "note",
        "a",
        "an",
        "the",
        "for",
        "to",
        "contact",
        "person",
        "please",
        "can",
        "you",
    ]

    inputs = [
        MessageTextInput(
            name="text_input",
            display_name="Text Input",
            required=True,
            info="Natural language input like 'Ken about AI Transformation'",
        ),
    ]

    outputs = [
        Output(
            name="parsed_data",
            display_name="Parsed Data",
            method="parse",
        ),
    ]

    def parse(self) -> Data:
        """
        Parse the input text to extract contact identification and topic.

        Returns:
            Data object with:
            - contact_id: HubSpot contact ID if a 7+ digit number is found
            - contact_name: Extracted name to search for (if no ID)
            - topic: The topic/service type for the email
        """
        text = self.text_input.strip() if self.text_input else ""

        result = {
            "contact_id": None,
            "contact_name": None,
            "topic": None,
            "raw_input": text,
        }

        if not text:
            self.status = "No input provided"
            return Data(data=result)

        # 1. Look for contact ID (7+ digit number)
        contact_id_match = re.search(r"\b(\d{7,})\b", text)
        if contact_id_match:
            result["contact_id"] = contact_id_match.group(1)
            logger.info(f"Found contact ID: {result['contact_id']}")

        # 2. Extract topic - look for "about X" pattern
        topic_match = re.search(r"\babout\s+(.+)$", text, re.IGNORECASE)
        if topic_match:
            result["topic"] = topic_match.group(1).strip()
            logger.info(f"Found topic: {result['topic']}")

        # 3. If no contact ID, extract the name
        if not result["contact_id"] and result["topic"]:
            # Get everything before "about"
            name_part = re.sub(r"\s*about\s+.+$", "", text, flags=re.IGNORECASE)

            # Remove all filler/command words
            filler_pattern = r"\b(" + "|".join(self.FILLER_WORDS) + r")\b"
            name_part = re.sub(filler_pattern, "", name_part, flags=re.IGNORECASE)

            # Clean up extra whitespace
            name_part = " ".join(name_part.split()).strip()

            if name_part and len(name_part) >= 2:
                result["contact_name"] = name_part
                logger.info(f"Extracted contact name: {result['contact_name']}")

        # 4. If we have a contact ID but no topic, get topic from after the ID
        if result["contact_id"] and not result["topic"]:
            # Remove everything up to and including the contact ID
            remaining = re.sub(
                r".*?\b" + re.escape(result["contact_id"]) + r"\b\s*",
                "",
                text,
                count=1,
            )
            remaining = remaining.strip()

            # Also check for "about X" pattern in remaining
            topic_match = re.search(r"\babout\s+(.+)$", remaining, re.IGNORECASE)
            if topic_match:
                result["topic"] = topic_match.group(1).strip()
            elif remaining:
                result["topic"] = remaining
                logger.info(f"Topic from remainder: {result['topic']}")

        # Set status for UI
        if result["contact_id"]:
            self.status = f"ID: {result['contact_id']}, Topic: {result['topic']}"
        elif result["contact_name"]:
            self.status = f"Name: {result['contact_name']}, Topic: {result['topic']}"
        else:
            self.status = "Could not parse input"

        return Data(data=result)

import re

import pytest
from langbuilder.components.input_output import ChatInput, ChatOutput
from langbuilder.components.openai.openai_chat_model import OpenAIModelComponent
from langbuilder.components.processing import PromptComponent
from langbuilder.graph.graph.base import Graph


def test_edge_raises_error_on_invalid_target_handle():
    template = """Answer the user as if you were a pirate.

User: {user_input}

Answer:
"""
    chat_input = ChatInput()
    prompt_component = PromptComponent()
    prompt_component.set(
        template=template,
        user_input=chat_input.message_response,
    )

    openai_component = OpenAIModelComponent()
    openai_component.set(input_values=prompt_component.build_prompt)

    chat_output = ChatOutput()
    chat_output.set(input_value=openai_component.text_response)
    with pytest.raises(
        ValueError, match=re.escape("Component OpenAI field 'input_values' might not be a valid input.")
    ):
        Graph(start=chat_input, end=chat_output)

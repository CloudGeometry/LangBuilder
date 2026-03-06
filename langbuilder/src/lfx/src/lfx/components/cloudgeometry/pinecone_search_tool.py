"""
Pinecone Search Tool Component

Enables semantic search against Pinecone vector index.
Works both as a standalone flow component AND as an Agent tool.

Follows the AstraDB Tool pattern for dual-use components.

Adapted for LangBuilder 1.65+ (CloudGeometry fork)
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from lfx.base.langchain_utilities.model import LCToolComponent
from lfx.base.tools.constants import TOOL_OUTPUT_NAME, TOOL_OUTPUT_DISPLAY_NAME
from lfx.field_typing import Tool
from lfx.io import (
    BoolInput,
    DropdownInput,
    HandleInput,
    IntInput,
    MessageTextInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema.data import Data


class PineconeSearchToolComponent(LCToolComponent):
    """Semantic search against Pinecone vector index.

    This component performs semantic search using embeddings and returns
    the most similar documents. Works both as a flow component (connect
    query via edge) AND as an Agent tool.

    **Authentication:**
    - Set PINECONE_API_KEY environment variable, OR
    - Provide API key directly in the component

    **Embedding Options (priority order):**
    1. Connect an Embedding model component (recommended)
    2. Use Pinecone's inference API (set use_pinecone_inference=True)
    3. Fall back to OpenAI embeddings (requires OPENAI_API_KEY)

    **Usage as Flow Component:**
    - Connect an Embedding model to 'embedding' input (optional)
    - Set search query in component or connect via edge
    - Output is Data with search results

    **Usage as Agent Tool:**
    - Connect 'Tool' output to Agent's 'tools' input
    - Agent will call this when it needs to search for similar documents
    """

    display_name = "Pinecone Search Tool"
    description = "Search Pinecone vector index for semantically similar documents"
    documentation = "https://docs.pinecone.io/docs/query-data"
    icon = "Pinecone"
    name = "PineconeSearchTool"

    inputs = [
        # Search query input - supports both flow (edge) and tool (Agent) usage
        MessageTextInput(
            name="search_query",
            display_name="Search Query",
            info="The search query - describe what you're looking for semantically. Connect via edge for deterministic flows.",
            required=False,
            tool_mode=True,
        ),

        # Tool configuration
        StrInput(
            name="tool_name",
            display_name="Tool Name",
            info="The name of the tool to be passed to the LLM.",
            value="pinecone_search",
            required=True,
        ),
        StrInput(
            name="tool_description",
            display_name="Tool Description",
            info="Describe the tool to LLM. Add any information that can help the LLM use the tool.",
            value="Search for semantically similar documents in Pinecone. Use this to find existing PRDs, feature requests, or documentation related to what the user is asking about.",
            required=True,
        ),

        # Pinecone configuration
        SecretStrInput(
            name="pinecone_api_key",
            display_name="Pinecone API Key",
            info="Pinecone API key. Leave empty to use PINECONE_API_KEY env var.",
            required=False,
        ),
        StrInput(
            name="index_name",
            display_name="Index Name",
            info="Name of the Pinecone index to search.",
            required=True,
        ),
        StrInput(
            name="namespace",
            display_name="Namespace",
            info="Optional namespace within the index.",
            required=False,
        ),
        IntInput(
            name="number_of_results",
            display_name="Number of Results",
            info="Number of results to return.",
            value=5,
            advanced=True,
        ),

        # Embedding configuration
        HandleInput(
            name="embedding",
            display_name="Embedding Model",
            input_types=["Embeddings"],
            info="Embedding model to use. If not provided, falls back to OpenAI or Pinecone inference.",
        ),
        BoolInput(
            name="use_pinecone_inference",
            display_name="Use Pinecone Inference",
            info="Use Pinecone's inference API for embeddings (uses your Pinecone API key).",
            value=False,
            advanced=True,
        ),
        DropdownInput(
            name="pinecone_embed_model",
            display_name="Pinecone Embedding Model",
            info="Pinecone embedding model to use (only when Use Pinecone Inference is enabled).",
            value="multilingual-e5-large",
            options=["multilingual-e5-large", "llama-text-embed-v2"],
            advanced=True,
        ),
        SecretStrInput(
            name="openai_api_key",
            display_name="OpenAI API Key (Fallback)",
            info="OpenAI API key for embeddings fallback. Leave empty to use OPENAI_API_KEY env var.",
            required=False,
            advanced=True,
        ),
        StrInput(
            name="openai_model",
            display_name="OpenAI Embedding Model",
            info="OpenAI embedding model to use as fallback.",
            value="text-embedding-3-small",
            advanced=True,
        ),
        IntInput(
            name="openai_dimensions",
            display_name="OpenAI Embedding Dimensions",
            info="Dimension of OpenAI embeddings. Set to 1024 to match Pinecone inference models, or 1536 for full text-embedding-3-small quality. Must match your index dimensions.",
            value=1024,
            advanced=True,
        ),
    ]

    # Override outputs to use component_as_tool naming for proper frontend tool mode detection
    outputs = [
        Output(name="api_run_model", display_name="Data", method="run_model"),
        Output(
            name=TOOL_OUTPUT_NAME,  # "component_as_tool"
            display_name=TOOL_OUTPUT_DISPLAY_NAME,  # "Toolset"
            method="to_toolkit",  # Uses to_toolkit which calls _get_tools() -> build_tool()
            types=["Tool"],
        ),
    ]

    # Caching
    _cached_index: Any = None
    _cached_pc: Any = None

    def _get_pinecone_client(self):
        """Get or create cached Pinecone client."""
        if self._cached_pc is not None:
            return self._cached_pc

        try:
            from pinecone import Pinecone
        except ImportError as e:
            msg = "pinecone is not installed. Install with: pip install pinecone"
            raise ImportError(msg) from e

        # Get API key
        api_key = self.pinecone_api_key
        if hasattr(api_key, "get_secret_value"):
            api_key = api_key.get_secret_value()
        api_key = api_key or os.environ.get("PINECONE_API_KEY", "")

        if not api_key:
            msg = "Pinecone API key not configured. Set PINECONE_API_KEY env var or provide in component."
            raise ValueError(msg)

        self._cached_pc = Pinecone(api_key=api_key)
        return self._cached_pc

    def _get_index(self):
        """Get or create cached Pinecone index."""
        if self._cached_index is not None:
            return self._cached_index

        pc = self._get_pinecone_client()
        self._cached_index = pc.Index(self.index_name)
        return self._cached_index

    def _get_embedding(self, text: str, input_type: str = "query") -> list[float]:
        """Get embedding for text using configured method.

        Priority:
        1. External embedding component (if connected)
        2. Pinecone inference API (if enabled)
        3. OpenAI fallback

        Args:
            text: The text to embed
            input_type: "query" for search queries, "passage" for documents to store
        """
        # 1. Use external embedding if provided
        if self.embedding is not None:
            return self.embedding.embed_query(text)

        # 2. Use Pinecone inference API
        if self.use_pinecone_inference:
            pc = self._get_pinecone_client()
            model = getattr(self, "pinecone_embed_model", None) or "multilingual-e5-large"
            result = pc.inference.embed(
                model=model,
                inputs=[text],
                parameters={"input_type": input_type, "truncate": "END"}
            )
            # EmbeddingsList is directly indexable, each item has 'values' key
            # See: https://docs.pinecone.io/guides/inference/generate-embeddings
            return result[0]['values']

        # 3. Fall back to OpenAI
        try:
            from openai import OpenAI
        except ImportError as e:
            msg = "openai is not installed. Install with: pip install openai"
            raise ImportError(msg) from e

        openai_key = self.openai_api_key
        if hasattr(openai_key, "get_secret_value"):
            openai_key = openai_key.get_secret_value()
        openai_key = openai_key or os.environ.get("OPENAI_API_KEY", "")

        if not openai_key:
            msg = "No embedding method available. Connect an Embedding model, enable Pinecone inference, or set OPENAI_API_KEY."
            raise ValueError(msg)

        client = OpenAI(api_key=openai_key)
        # Use dimensions parameter for text-embedding-3 models to match index dimensions
        # Default 1024 matches Pinecone inference models (multilingual-e5-large, llama-text-embed-v2)
        dimensions = getattr(self, "openai_dimensions", None) or 1024
        response = client.embeddings.create(
            input=text,
            model=self.openai_model or "text-embedding-3-small",
            dimensions=dimensions
        )
        return response.data[0].embedding

    def run_model(self, search_query: str = "", **kwargs) -> list[Data]:
        """Run search against Pinecone.

        Args:
            search_query: The search query text (from tool call)
            **kwargs: Additional arguments (ignored)

        Returns:
            List of Data objects with search results
        """
        # Priority: tool argument > component attribute (from edge)
        query = search_query
        if not query:
            # Check component attribute (set via edge connection)
            query = getattr(self, "search_query", "") or ""
            if hasattr(query, "text"):
                query = query.text
            query = str(query)

        if not query or not query.strip():
            self.status = "No search query provided"
            return []

        query = query.strip()
        self.log(f"Searching for: {query[:100]}...")

        try:
            index = self._get_index()

            # Build query kwargs
            query_kwargs = {
                "top_k": self.number_of_results or 5,
                "include_metadata": True,
            }
            if self.namespace:
                query_kwargs["namespace"] = self.namespace

            # Get embedding using configured method (external, Pinecone inference, or OpenAI)
            self.status = "Creating embedding..."
            embedding = self._get_embedding(query, input_type="query")
            query_kwargs["vector"] = embedding

            # Execute search
            self.status = "Searching Pinecone..."
            results = index.query(**query_kwargs)

            # Format results
            data_list = []
            for match in results.get("matches", []):
                data_list.append(Data(data={
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "metadata": match.get("metadata", {}),
                    "text": match.get("metadata", {}).get("text", ""),
                    "title": match.get("metadata", {}).get("title", match.get("id")),
                }))

            self.status = f"Found {len(data_list)} results"
            self.log(f"Search complete: {len(data_list)} matches")
            return data_list

        except Exception as e:
            self.status = f"Error: {e}"
            self.log(f"Search error: {e}")
            raise ValueError(f"Pinecone search failed: {e}") from e

    async def _get_tools(self):
        """Override to return the named tool from build_tool() instead of generic outputs."""
        tool = self.build_tool()
        if tool and not tool.tags:
            tool.tags = [tool.name]
        return [tool] if tool else []

    def build_tool(self) -> Tool:
        """Build the Pinecone search tool for Agent use."""

        # Create dynamic args schema
        args: dict[str, tuple[Any, Field]] = {
            "search_query": (str, Field(description="The search query - describe what you're looking for semantically"))
        }
        ToolInput = create_model("ToolInput", **args, __base__=BaseModel)

        tool = StructuredTool.from_function(
            name=self.tool_name,
            description=self.tool_description,
            args_schema=ToolInput,
            func=self.run_model,
            return_direct=False,
            tags=[self.tool_name],
        )

        self.status = f"Tool '{self.tool_name}' created"
        return tool

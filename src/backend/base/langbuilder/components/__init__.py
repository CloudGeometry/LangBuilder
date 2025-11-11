"""LangBuilder Components module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langbuilder.components._importing import import_mod

if TYPE_CHECKING:
    from langbuilder.components import (
        Notion,
        agentql,
        agents,
        aiml,
        amazon,
        anthropic,
        apify,
        arxiv,
        assemblyai,
        azure,
        baidu,
        bing,
        cleanlab,
        cloudflare,
        cohere,
        composio,
        confluence,
        crewai,
        custom_component,
        data,
        datastax,
        deepseek,
        docling,
        duckduckgo,
        embeddings,
        exa,
        firecrawl,
        git,
        glean,
        google,
        groq,
        helpers,
        homeassistant,
        huggingface,
        ibm,
        icosacomputing,
        input_output,
        langchain_utilities,
        langwatch,
        lmstudio,
        logic,
        maritalk,
        mem0,
        mistral,
        models,
        needle,
        notdiamond,
        novita,
        nvidia,
        olivya,
        ollama,
        openai,
        openrouter,
        perplexity,
        processing,
        prototypes,
        redis,
        sambanova,
        scrapegraph,
        searchapi,
        serpapi,
        tavily,
        tools,
        twelvelabs,
        unstructured,
        vectorstores,
        vertexai,
        wikipedia,
        wolframalpha,
        xai,
        yahoosearch,
        youtube,
        zep,
    )

_dynamic_imports = {
    "agents": "langbuilder.components.agents",
    "data": "langbuilder.components.data",
    "processing": "langbuilder.components.processing",
    "vectorstores": "langbuilder.components.vectorstores",
    "tools": "langbuilder.components.tools",
    "models": "langbuilder.components.models",
    "embeddings": "langbuilder.components.embeddings",
    "helpers": "langbuilder.components.helpers",
    "input_output": "langbuilder.components.input_output",
    "logic": "langbuilder.components.logic",
    "custom_component": "langbuilder.components.custom_component",
    "prototypes": "langbuilder.components.prototypes",
    "openai": "langbuilder.components.openai",
    "anthropic": "langbuilder.components.anthropic",
    "google": "langbuilder.components.google",
    "azure": "langbuilder.components.azure",
    "huggingface": "langbuilder.components.huggingface",
    "ollama": "langbuilder.components.ollama",
    "groq": "langbuilder.components.groq",
    "cohere": "langbuilder.components.cohere",
    "mistral": "langbuilder.components.mistral",
    "deepseek": "langbuilder.components.deepseek",
    "nvidia": "langbuilder.components.nvidia",
    "amazon": "langbuilder.components.amazon",
    "vertexai": "langbuilder.components.vertexai",
    "xai": "langbuilder.components.xai",
    "perplexity": "langbuilder.components.perplexity",
    "openrouter": "langbuilder.components.openrouter",
    "lmstudio": "langbuilder.components.lmstudio",
    "sambanova": "langbuilder.components.sambanova",
    "maritalk": "langbuilder.components.maritalk",
    "novita": "langbuilder.components.novita",
    "olivya": "langbuilder.components.olivya",
    "notdiamond": "langbuilder.components.notdiamond",
    "needle": "langbuilder.components.needle",
    "cloudflare": "langbuilder.components.cloudflare",
    "baidu": "langbuilder.components.baidu",
    "aiml": "langbuilder.components.aiml",
    "ibm": "langbuilder.components.ibm",
    "langchain_utilities": "langbuilder.components.langchain_utilities",
    "crewai": "langbuilder.components.crewai",
    "composio": "langbuilder.components.composio",
    "mem0": "langbuilder.components.mem0",
    "datastax": "langbuilder.components.datastax",
    "cleanlab": "langbuilder.components.cleanlab",
    "langwatch": "langbuilder.components.langwatch",
    "icosacomputing": "langbuilder.components.icosacomputing",
    "homeassistant": "langbuilder.components.homeassistant",
    "agentql": "langbuilder.components.agentql",
    "assemblyai": "langbuilder.components.assemblyai",
    "twelvelabs": "langbuilder.components.twelvelabs",
    "docling": "langbuilder.components.docling",
    "unstructured": "langbuilder.components.unstructured",
    "redis": "langbuilder.components.redis",
    "zep": "langbuilder.components.zep",
    "bing": "langbuilder.components.bing",
    "duckduckgo": "langbuilder.components.duckduckgo",
    "serpapi": "langbuilder.components.serpapi",
    "searchapi": "langbuilder.components.searchapi",
    "tavily": "langbuilder.components.tavily",
    "exa": "langbuilder.components.exa",
    "glean": "langbuilder.components.glean",
    "yahoosearch": "langbuilder.components.yahoosearch",
    "apify": "langbuilder.components.apify",
    "arxiv": "langbuilder.components.arxiv",
    "confluence": "langbuilder.components.confluence",
    "firecrawl": "langbuilder.components.firecrawl",
    "git": "langbuilder.components.git",
    "wikipedia": "langbuilder.components.wikipedia",
    "youtube": "langbuilder.components.youtube",
    "scrapegraph": "langbuilder.components.scrapegraph",
    "Notion": "langbuilder.components.Notion",
    "wolframalpha": "langbuilder.components.wolframalpha",
}

__all__: list[str] = [
    "Notion",
    "agentql",
    "agents",
    "aiml",
    "amazon",
    "anthropic",
    "apify",
    "arxiv",
    "assemblyai",
    "azure",
    "baidu",
    "bing",
    "cleanlab",
    "cloudflare",
    "cohere",
    "composio",
    "confluence",
    "crewai",
    "custom_component",
    "data",
    "datastax",
    "deepseek",
    "docling",
    "duckduckgo",
    "embeddings",
    "exa",
    "firecrawl",
    "git",
    "glean",
    "google",
    "groq",
    "helpers",
    "homeassistant",
    "huggingface",
    "ibm",
    "icosacomputing",
    "input_output",
    "langchain_utilities",
    "langwatch",
    "lmstudio",
    "logic",
    "maritalk",
    "mem0",
    "mistral",
    "models",
    "needle",
    "notdiamond",
    "novita",
    "nvidia",
    "olivya",
    "ollama",
    "openai",
    "openrouter",
    "perplexity",
    "processing",
    "prototypes",
    "redis",
    "sambanova",
    "scrapegraph",
    "searchapi",
    "serpapi",
    "tavily",
    "tools",
    "twelvelabs",
    "unstructured",
    "vectorstores",
    "vertexai",
    "wikipedia",
    "wolframalpha",
    "xai",
    "yahoosearch",
    "youtube",
    "zep",
]


def __getattr__(attr_name: str) -> Any:
    """Lazily import component modules on attribute access.

    Args:
        attr_name (str): The attribute/module name to import.

    Returns:
        Any: The imported module or attribute.

    Raises:
        AttributeError: If the attribute is not a known component or cannot be imported.
    """
    if attr_name not in _dynamic_imports:
        msg = f"module '{__name__}' has no attribute '{attr_name}'"
        raise AttributeError(msg)
    try:
        # Use import_mod as in LangChain, passing the module name and package
        result = import_mod(attr_name, "__module__", __spec__.parent)
    except (ModuleNotFoundError, ImportError, AttributeError) as e:
        msg = f"Could not import '{attr_name}' from '{__name__}': {e}"
        raise AttributeError(msg) from e
    globals()[attr_name] = result  # Cache for future access
    return result


def __dir__() -> list[str]:
    """Return list of available attributes for tab-completion and dir()."""
    return list(__all__)


# Optional: Consistency check (can be removed in production)
_missing = set(__all__) - set(_dynamic_imports)
if _missing:
    msg = f"Missing dynamic import mapping for: {', '.join(_missing)}"
    raise ImportError(msg)

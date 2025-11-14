from langchain_core.vectorstores import VectorStoreRetriever

from langbuilder.custom.custom_component.custom_component import CustomComponent
from langbuilder.field_typing import VectorStore
from langbuilder.inputs.inputs import HandleInput


class VectorStoreRetrieverComponent(CustomComponent):
    display_name = "VectorStore Retriever"
    description = "A vector store retriever"
    name = "VectorStoreRetriever"
    icon = "LangChain"

    inputs = [
        HandleInput(
            name="vectorstore",
            display_name="Vector Store",
            input_types=["VectorStore"],
            required=True,
        ),
    ]

    def build(self, vectorstore: VectorStore) -> VectorStoreRetriever:
        return vectorstore.as_retriever()

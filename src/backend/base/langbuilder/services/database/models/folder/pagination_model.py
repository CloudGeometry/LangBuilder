from fastapi_pagination import Page

from langbuilder.helpers.base_model import BaseModel
from langbuilder.services.database.models.flow.model import Flow
from langbuilder.services.database.models.folder.model import FolderRead


class FolderWithPaginatedFlows(BaseModel):
    folder: FolderRead
    flows: Page[Flow]

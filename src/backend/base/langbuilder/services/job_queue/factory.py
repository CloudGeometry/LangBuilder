from langbuilder.services.base import Service
from langbuilder.services.factory import ServiceFactory
from langbuilder.services.job_queue.service import JobQueueService


class JobQueueServiceFactory(ServiceFactory):
    def __init__(self):
        super().__init__(JobQueueService)

    def create(self) -> Service:
        return JobQueueService()

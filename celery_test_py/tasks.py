import os
from celery import Celery
import logging
from celery.canvas import Signature
from celery.result import AsyncResult

from celery.utils.log import get_task_logger

logging.basicConfig(level=logging.DEBUG)
task_logger = get_task_logger(__name__)
task_logger.setLevel(logging.DEBUG)

celery = Celery('celery-test',
                broker=os.environ['REDIS_ADDR'],
                backend=os.environ['REDIS_ADDR'])

# celery.conf.update(
#     task_routes={
#         'podwriter_semantic_search.tasks.index_transcript': {'queue': 'index'},
#         'podwriter_semantic_search.tasks.delete_index': {'queue': 'index'},
#         'podwriter_semantic_search.tasks.search': {'queue': 'search'},
#         'podwriter_semantic_search.tasks.ping': {'queue': 'ping'},
#     }
# )

@celery.task(name='add')
def add(x: int, y: int):
    return x + y


if __name__ == '__main__':
    result: AsyncResult = add.delay(1, 2)
    print(f"waiting for result: {result.id}")
    print(result.get())

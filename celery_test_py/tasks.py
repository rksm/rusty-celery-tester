import os
from celery import Celery
import logging

from celery.utils.log import get_task_logger

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
    # resut = add.delay(id='___', x=1, y=2)
    # print(resut.get())
    # add.apply_async(kwargs={'id': '___', 'x': 1, 'y': 2})
    # add.apply_async(kwargs={'id': '___', 'x': 1, 'y': 2})
    print("started")

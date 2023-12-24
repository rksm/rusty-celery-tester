import os
from celery import Celery
import logging
from celery.result import AsyncResult
import time

from celery.utils.log import get_task_logger

logging.basicConfig(level=logging.INFO)
task_logger = get_task_logger(__name__)
task_logger.setLevel(logging.INFO)

celery = Celery('celery-test',
                broker=os.environ['REDIS_ADDR'],
                backend=os.environ['REDIS_ADDR'])

celery.conf.update(
    broker_connection_retry_on_startup=True,

    # task_routes={
    #     'podwriter_semantic_search.tasks.index_transcript': {'queue': 'index'},
    #     'podwriter_semantic_search.tasks.delete_index': {'queue': 'index'},
    #     'podwriter_semantic_search.tasks.search': {'queue': 'search'},
    #     'podwriter_semantic_search.tasks.ping': {'queue': 'ping'},
    # }
)

@celery.task(name='add')
def add(x: int, y: int):
    return x + y

@celery.task(name='expected_failure')
def expected_failure():
    raise Exception("expected")

@celery.task(name='unexpected_failure')
def unexpected_failure():
    raise Exception("unexpected")

@celery.task(name='task_with_timeout', time_limit=1)
def task_with_timeout():
    time.sleep(2)


if __name__ == '__main__':
    result: AsyncResult = add.delay(1, 2)
    assert result.get() == 3

    result: AsyncResult = expected_failure.delay()
    try:
        result.get()
        assert False
    except Exception as e:
        assert str(e) == "expected"

import os
from celery import Celery
import logging
from celery.app.autoretry import Retry
from celery.result import AsyncResult
import time
import argparse
from datetime import datetime

from celery.utils.log import get_task_logger

logging.basicConfig(level=logging.INFO)
task_logger = get_task_logger(__name__)
task_logger.setLevel(logging.INFO)

celery = Celery('celery-test',
                broker=os.environ['CELERY_BROKER'],
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


expected_failure_count = 0

@celery.task(bind=True, name='expected_failure', time_limit=60, max_retries=3)
def expected_failure(self):
    global expected_failure_count
    time.sleep(1)
    task_logger.info(f"expected_failure_count={expected_failure_count}")
    expected_failure_count += 1
    if expected_failure_count == 30:
        return
    else:
        # raise Exception("expected")
        raise self.retry(countdown=1)

@celery.task(name='unexpected_failure')
def unexpected_failure():
    raise Exception("unexpected")

@celery.task(name='task_with_timeout', time_limit=1)
def task_with_timeout():
    time.sleep(2)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument("--task",
                        choices=["add", "expected_failure", "unexpected_failure", "task_with_timeout"],
                        required=True, nargs="+")

    args = parser.parse_args()

    for task in args.task:

        logger.info(f"running task {task}")

        if task == "add":
            result: AsyncResult = add.delay(1, 2)
            assert result.get() == 3

        if task == "expected_failure":
            result: AsyncResult = expected_failure.delay()
            try:
                result.get()
                assert False
            except Exception as e:
                assert str(e) == "failure expected"

        if task == "unexpected_failure":
            result: AsyncResult = unexpected_failure.delay()
            try:
                result.get()
                assert False
            except Exception as e:
                assert str(e) == "failure unexpected"

        if task == "task_with_timeout":
            result: AsyncResult = task_with_timeout.delay()
            try:
                result.get()
                assert False
            except Exception as e:
                assert str(e) == "failure unexpected"

        logger.info(f"task {task} succeeded")

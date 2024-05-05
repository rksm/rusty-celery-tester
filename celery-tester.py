#!/usr/bin/env python

import argparse
from typing import Literal
import dotenv
import logging
import os
import subprocess as sp
import time
from threading import Thread

logger = logging.getLogger(__name__)

Broker = Literal["redis", "amqp"]

class BackendContext:

    def __init__(self, name: str):
        self.name = name
        self.started_new_container = False

    @property
    def kind(self):
        return self.name.split("-")[0]

    def start(self):
        raise NotImplementedError()

    def __enter__(self):
        # Perform the setup (start redis if not running)
        kind = self.kind
        logger.debug(f"starting {kind} docker container")
        running = sp.run(["docker", "ps", "-q", "-f", f"name={self.name}"], stdout=sp.PIPE)

        if not running.stdout.strip():
            # If the container is not running, start a new one
            logger.debug(f"{kind} container not running, starting")
            self.start()
            self.started_new_container = True
            logger.debug(f"{kind} container started")
        else:
            logger.debug("{kind} already running")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Perform the teardown
        if self.started_new_container:
            logger.debug("stopping redis docker container")
            sp.run(["docker", "stop", self.name])
            logger.debug("redis container stopped")


class RedisContext(BackendContext):

    def __init__(self):
        super().__init__("redis-celery-test")

    def start(self):
        sp.run(["docker", "run", "-d", "--rm", "-p", "6380:6379", "--name", self.name, "redis/redis-stack"])


class AmqpContext(BackendContext):

        def __init__(self):
            super().__init__("rabbitmq-celery-test")

        def start(self):
            sp.run(["docker", "run", "-d", "--rm", "-p", "5672:5672", "-p", "15672:15672", "--name", self.name, "rabbitmq:3-management"])


class VerbosePopen(sp.Popen):

    def __init__(self, name, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)
        Thread(target=self.report_output, args=(self.stdout, )).start()
        Thread(target=self.report_output, args=(self.stderr, )).start()

    def report_output(self, stream):
        for line in stream:
            print(f"[{self.name}] {line.decode('utf-8').strip()}")


class RustWorker:

    def __init__(self, broker: Broker):
        self.broker = broker

    def __enter__(self):
        self.proc = VerbosePopen("worker", ["cargo", "run", "--", "worker", "--broker", self.broker],
                                 stdout=sp.PIPE,
                                 stderr=sp.PIPE,
                                 cwd="rust")
        time.sleep(1)
        assert not self.crashed(), "worker crashed"
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert not self.crashed(), "worker crashed"
        self.proc.kill()

    def crashed(self) -> bool:
        return self.proc.poll() is not None


class PythonWorker:

    def __init__(self, verbose: bool, broker: Broker):
        self.verbose = verbose
        self.broker = broker

    def __enter__(self):
        self.proc = VerbosePopen("pyworker", ["python", "-m", "celery", "-A",
                                              "py.tasks",
                                              *(["-q"] if not self.verbose else []),
                                              "worker",
                                              "-l", "DEBUG" if self.verbose else "CRITICAL",
                                              "-c", "1"],
                                 env={**os.environ,
                                     "CELERY_BROKER": os.environ["REDIS_ADDR" if self.broker == "redis" else "AMQP_ADDR"]},
                                 stdout=sp.PIPE,
                                 stderr=sp.PIPE)
        time.sleep(1)
        assert not self.crashed(), "worker crashed"
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert not self.crashed(), "worker crashed"
        self.proc.kill()

    def crashed(self) -> bool:
        return self.proc.poll() is not None


TASKS = [
    "add",
    "expected_failure",
    "task_with_timeout",
    "unexpected_failure",
]


class Client(VerbosePopen):
    @classmethod
    def run(cls, tasks: list[str], broker: Broker):
        for task in tasks:
            logger.info(f"running task {task}")
            client = cls(task, broker)
            client.wait()
            assert client.returncode == 0, f"client failed for {task}"


class RustClient(Client):

    def __init__(self, task: str, broker: str):
        logger.info(f"running rust client for {task}")
        super().__init__(f"client-{task}",
                         ["cargo", "run", "--", "client", "--broker", broker, task],
                         stdout=sp.PIPE,
                         stderr=sp.PIPE,
                         cwd="rust")


class PythonClient(Client):

    def __init__(self, task: str, broker: str):
        logger.info(f"running python client for {task}")
        super().__init__(f"pyclient-{task}",
                         ["python", "-m", "py.tasks", "--task", task],
                         env={**os.environ,
                             "CELERY_BROKER": os.environ["REDIS_ADDR" if broker == "redis" else "AMQP_ADDR"]},
                         stdout=sp.PIPE,
                         stderr=sp.PIPE)


def main(args: argparse.Namespace):
    context = RedisContext() if args.broker == "redis" else AmqpContext()
    with context:
        workers = []
        if args.rust_worker:
            workers.append(RustWorker(broker=args.broker))
        if args.python_worker:
            workers.append(PythonWorker(verbose=args.verbose, broker=args.broker))
        clients = []
        if args.rust_client:
            clients.append(RustClient)
        if args.python_client:
            clients.append(PythonClient)
        for worker in workers:
            with worker:
                for client in clients:
                    client.run(args.tasks, args.broker)


if __name__ == "__main__":
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-worker", action="store_true")
    parser.add_argument("--python-worker", action="store_true")
    parser.add_argument("--rust-client", action="store_true")
    parser.add_argument("--python-client", action="store_true")
    parser.add_argument("--tasks", nargs="+", choices=["add", "expected_failure", "unexpected_failure", "task_with_timeout"], help="If not set, all tasks are run")
    parser.add_argument("--broker", choices=["redis", "amqp"], default="redis")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not args.tasks:
        args.tasks = TASKS

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
        logger.setLevel(logging.DEBUG)
        os.environ["RUST_LOG"] = "debug,celery=trace"
        os.environ["RUST_BACKTRACE"] = "1"
    else:
        logging.basicConfig(level=logging.WARNING)
        logger.setLevel(logging.INFO)
        os.environ["RUST_LOG"] = "info"

    main(args)
    logger.info("done")

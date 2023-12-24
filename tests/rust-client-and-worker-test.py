#!/usr/bin/env python

import argparse
import dotenv
import logging
import os
import subprocess as sp
import time
from threading import Thread

logger = logging.getLogger(__name__)

class RedisContext:

    def __init__(self):
        self.name = "redis-celery-test"
        self.started_new_container = False

    def __enter__(self):
        # Perform the setup (start redis if not running)
        logger.debug("starting redis docker container")
        running = sp.run(["docker", "ps", "-q", "-f", f"name={self.name}"],
                         stdout=sp.PIPE)

        if not running.stdout.strip():
            # If the container is not running, start a new one
            sp.run([
                "docker", "run", "-d", "--rm", "-p", "6380:6379", "--name",
                self.name, "redis/redis-stack"
            ])
            self.started_new_container = True
            logger.debug("redis container started")
        else:
            logger.debug("redis already running")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Perform the teardown
        if self.started_new_container:
            logger.debug("stopping redis docker container")
            sp.run(["docker", "stop", self.name])
            logger.debug("redis container stopped")


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

    def __enter__(self):
        self.proc = VerbosePopen("worker", ["cargo", "run", "--", "worker"],
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


class PythonWorker:

    def __init__(self, verbose: bool):
        self.verbose = verbose

    def __enter__(self):
        self.proc = VerbosePopen("pyworker", ["./venv/bin/python", "-m", "celery", "-A",
                                              "celery_test_py.tasks",
                                              *(["-q"] if not self.verbose else []),
                                              "worker",
                                              "-l", "DEBUG" if self.verbose else "CRITICAL",
                                              "-c", "1"],
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


class Client(VerbosePopen):
    @classmethod
    def run(cls):
        tasks = [
            "add",
            "expected_failure",
            "task_with_timeout",
            "unexpected_failure",
        ]

        for task in tasks:
            logger.info(f"running task {task}")
            client = cls(task)
            client.wait(timeout=10)
            assert client.returncode == 0, f"client failed for {task}"


class RustClient(Client):

    def __init__(self, task: str):
        logger.info(f"running rust client for {task}")
        super().__init__(f"client-{task}",
                         ["cargo", "run", "--", "client", task],
                         stdout=sp.PIPE,
                         stderr=sp.PIPE)


class PythonClient(Client):

    def __init__(self, task: str):
        logger.info(f"running python client for {task}")
        super().__init__(f"pyclient-{task}",
                         ["./venv/bin/python", "-m", "celery_test_py.tasks"],
                         stdout=sp.PIPE,
                         stderr=sp.PIPE)


def main(args: argparse.Namespace):
    with RedisContext():
        workers = []
        if args.rust_worker:
            workers.append(RustWorker())
        if args.python_worker:
            workers.append(PythonWorker(verbose=args.verbose))
        clients = []
        if args.rust_client:
            clients.append(RustClient)
        if args.python_client:
            clients.append(PythonClient)
        for worker in workers:
            with worker:
                for client in clients:
                    client.run()


if __name__ == "__main__":
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-worker", action="store_true")
    parser.add_argument("--python-worker", action="store_true")
    parser.add_argument("--rust-client", action="store_true")
    parser.add_argument("--python-client", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

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

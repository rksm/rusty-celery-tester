# rust celery tester

What is this? You can test the
[rusty-celery](https://github.com/rusty-celery/rusty-celery/) crate with this
project, in particular the celery interop between Rust and Python.

## How to use

If you have nix installed just run `direnv allow`, otherwise make sure that you have `just` installed and run `just venv`.

Then to start redis and rabbitmq run `just backend-start` (you can stop it with `just backend-stop`).

The [celery-tester.py](./celery-tester.py) script does most of the heavy lifting:

```
$ ./celery-tester.py --help
usage: celery-tester.py [-h] [--rust-worker] [--python-worker] [--rust-client] [--python-client]
                        [--tasks {add,expected_failure,unexpected_failure,task_with_timeout} [{add,expected_failure,unexpected_failure,task_with_timeout} ...]]
                        [--broker {redis,amqp}] [--verbose]

options:
  -h, --help            show this help message and exit
  --rust-worker
  --python-worker
  --rust-client
  --python-client
  --tasks {add,expected_failure,unexpected_failure,task_with_timeout} [{add,expected_failure,unexpected_failure,task_with_timeout} ...]
                        If not set, all tasks are run
  --broker {redis,amqp}
  --verbose, -v
```

So e.g. to test celery for the `add` task with a Rust worker and a Python client you can run:

```
$ ./celery-tester.py --rust-worker --python-client --tasks add
```

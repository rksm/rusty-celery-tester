set dotenv-load

export RUST_BACKTRACE := "full"
export RUST_LOG := "debug"

default:
    just --list

run *args='':
    cargo run -- {{ args }}

rust-worker:
    just run worker

rust-master:
    just run master

dev *args='':
    cargo watch -x run -- {{ args }}

example:
    runall --names "master,worker" \
    'just rust-master' \
    'just rust-worker'

rabbitmq:
    docker-compose up -d

reset-backend:
    just rabbitmq-docker-stop || true
    just redis-docker-stop || true

redis-docker:
    docker run --rm -d -p 6379:6379 --name redis-celery-test redis/redis-stack

redis-docker-stop:
    docker stop redis-celery-test

rabbitmq-docker:
    docker run --rm -d -p 5672:5672 -p 15672:15672 --name rabbitmq-celery-test rabbitmq:3-management

rabbitmq-docker-stop:
    docker stop rabbitmq-celery-test

redis-cli *args="":
    docker exec -it redis-celery-test redis-cli {{ args }}

venv:
    python -m venv venv

pip-install:
    ./venv/bin/pip install -r requirements.txt

python *args="":
    ./venv/bin/python {{ args }}

python-master:
    just python -m celery_test_py.tasks

python-worker:
    just python -m celery -A celery_test_py.tasks worker -l DEBUG -c 1

python-worker-watch:
    fd -e py | entr -r just celery-python-worker

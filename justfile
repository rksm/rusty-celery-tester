default:
    just --list

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# rust

run *args='':
    cd rust && cargo run -- {{ args }}

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

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# python

venv:
    python -m venv .venv

pip-install:
    ./.venv/bin/pip install -r requirements.txt

python *args="":
    python {{ args }}

python-master:
    just python -m celery_test_py.tasks

python-worker:
    just python -m celery -A celery_test_py.tasks worker -l DEBUG -c 1

python-worker-watch:
    fd -e py | entr -r just celery-python-worker

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# backend

backend-start: redis rabbitmq

backend-stop:
    just rabbitmq-stop || true
    just redis-stop || true

redis:
    docker run --rm -d -p 6379:6379 --name redis-celery-test redis/redis-stack

redis-stop:
    docker stop redis-celery-test

rabbitmq:
    docker run --rm -d -p 5672:5672 -p 15672:15672 --name rabbitmq-celery-test rabbitmq:3-management

rabbitmq-stop:
    docker stop rabbitmq-celery-test

redis-cli *args="":
    docker exec -it redis-celery-test redis-cli {{ args }}

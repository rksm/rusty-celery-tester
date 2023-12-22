set dotenv-load

export RUST_BACKTRACE := "1"

default:
    just --list

run *args='':
    cargo run -- {{ args }}

dev *args='':
    cargo watch -x run -- {{ args }}

example:
    runall \
    'just run master' \
    'just run worker'

rabbitmq:
    docker-compose up -d

redis-cli *args="":
    docker exec -it redis-celery-test redis-cli {{ args }}

venv:
    python -m venv venv

pip-install:
    ./venv/bin/pip install -r requirements.txt

python *args="":
    ./venv/bin/python {{ args }}

set dotenv-load

# create .venv
start:
  python -m venv .venv && \
  source .venv/bin/activate && \
  python -m pip install -U pip && \
  python -m pip install -U \
    --editable '.[dev]' \
    --require-virtualenv \
    --verbose

dumpenv:
  op inject -i env.example -o .env

# upload to pypi
publish:
  python -m build && \
  python -m twine upload dist/* -u __token__ -p $PYPI_TOKEN

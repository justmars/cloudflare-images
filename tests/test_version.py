import pathlib

import tomllib

import cloudflare_images


def test_version():
    path = pathlib.Path("pyproject.toml")
    data = tomllib.loads(path.read_text())
    version = data["tool"]["poetry"]["version"]
    assert version == cloudflare_images.__version__

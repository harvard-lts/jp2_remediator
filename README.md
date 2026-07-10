# jp2_remediator

<!-- test and coverage badge from https://github.com/harvard-lts/etd-base-template/wiki --><a href="https://github.com/harvard-lts/jp2_remediator/actions/workflows/test.yml"><img src="https://github.com/harvard-lts/jp2_remediator/actions/workflows/test.yml/badge.svg"></a> <a href="https://github.com/harvard-lts/jp2_remediator/actions/workflows/test.yml"><img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/kimpham54/67d4eba1556653d896d2d36fcb3e5c7c/raw/covbadge.json"></a>
<!-- pypi badge from https://badge.fury.io/for/py/jp2_remediator --><a href="https://pypi.org/project/jp2_remediator"><img src="https://badge.fury.io/py/jp2-remediator.svg" alt="PyPI version" height="18"></a>

A Python module to validate jp2 images:
- reads the bytes of a jp2 file or directory of files or S3 bucket
- looks for presence of ICC profile
- maps and validates curv values according to the ISO/IEC 15444-1:2019 (E) and ICC.1:2022 Specifications
- corrects values where the rTRC/gTRC/bTRC tag size in the Tag table structure (ICC.1:2022 Table 24 tag size) is not the same as the count value (gamma, where n == 1) in the curveType encoding (ICC.1:2022 Table 35, n value)
- flag and (optionally) log values where the count value n != 1 for future review

<a href="https://pypi.org/project/jp2_remediator/">jp2_remediator on PyPI</a>

## Installation

```bash
pip install jp2_remediator
python3 -m pip install jp2_remediator

pip install jp2_remediator==NN.NN.NN (version number)
```

## Usage

```bash
python3 src/jp2_remediator/main.py  -h

usage: main.py [-h] {file,directory,bucket} ...

JP2 file processor

options:
  -h, --help            show this help message and exit

Input source:
  {file,directory,bucket}
    file                Process a single JP2 file
    directory           Process all JP2 files in a directory
    bucket              Process all JP2 files in an S3 bucket
```

### Process one file
```bash
python3 src/jp2_remediator/main.py file tests/test-images/7514499.jp2

python3 src/jp2_remediator/main.py file tests/test-images/481014278.jp2
```

### Process directory
```bash
python3 src/jp2_remediator/main.py directory tests/test-images/
```

### Process all .jp2 files in an S3 bucket:
```bash
python3 src/jp2_remediator/main.py bucket remediation-folder
```

### Process only files with a specific prefix (folder):
```bash
python3 src/jp2_remediator/main.py bucket remediation-folder --prefix testbatch_20240923`
```

## Run tests

### Run integration tests
```bash
pytest src/jp2_remediator/tests/integration/
```

### Run unit tests
```bash
pytest src/jp2_remediator/tests/unit/
```

## Docker environment

Build Docker image
```bash
./bin/docker-build.sh
```

Run Docker container as executable
```bash
./bin/docker-run.sh -h
```

## Development environment
```bash
uv sync
export PYTHONPATH="${PYTHONPATH}:src"

uv run python src/jp2_remediator/main.py -h
```

## Publishing to PyPI

Add the following variable to your `.env`:

```
UV_PUBLISH_TOKEN=pypi-<token>
```

Set the version number in `pyproject.toml` to the version you wish to publish.

Run the following commands:

```
rm -rf dist/
uv build
uv publish
```

If you get a publish error, the following commands will set your `.env` variables into the shell and should work:

```
set -a
source .env
set +a
uv publish
```

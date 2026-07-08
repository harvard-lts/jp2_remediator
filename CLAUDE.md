# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python module that validates and remediates the embedded ICC color profile in
JP2 (JPEG2000) images. It reads a JP2's bytes, locates the `colr` box and its
`rTRC`/`gTRC`/`bTRC` tags, and corrects the ICC tag-table size (ICC.1:2022
Table 24) when it disagrees with the `curveType` field length derived from the
gamma `n` value (Table 35, field length = `2n + 12`). When `n != 1` the file is
flagged and remediation is skipped for review rather than modified.

## Commands

This project uses `uv`. Do not call `pip`/`python` directly — go through `uv`.

- Install/sync deps: `uv sync`
- Lint (must pass, enforced in CI): `uv run flake8 ./src`
- Run all unit tests: `uv run pytest src/jp2_remediator/tests/unit`
- Run integration tests (needs AWS creds): `uv run pytest src/jp2_remediator/tests/integration`
- Run a single test file: `uv run pytest src/jp2_remediator/tests/unit/test_box_reader.py`
- Run a single test: `uv run pytest src/jp2_remediator/tests/unit/test_box_reader.py::<test_name>`

`pyproject.toml` sets `pythonpath = [".", "src"]` for pytest, so tests import
`jp2_remediator` without extra setup. To run the CLI directly, set
`PYTHONPATH` to include `src` first:

    export PYTHONPATH="${PYTHONPATH}:src"
    uv run python src/jp2_remediator/main.py -h

### CLI subcommands (from src/jp2_remediator/main.py)

- `file <path>` — process a single JP2 file
- `directory <path>` — walk a directory and process every `*.jp2`
- `s3-file --input-bucket B --input-key K --output-bucket B --output-key K` —
  download one JP2 from S3, remediate, upload the modified file (skipped if
  remediation is not applicable)

Note: README.md's usage section is out of date (it shows a `bucket --prefix`
command). Trust `main.py` for the actual interface.

## Architecture

Flow: `main.py` builds a `Processor(BoxReaderFactory())`; each subcommand calls
`process_file` / `process_directory` / `process_s3_file`. The `Processor`
(`processor.py`) is the I/O orchestrator — filesystem walking, S3
download/upload via `boto3`, temp-file cleanup. It delegates all JP2 parsing to
a `BoxReader` obtained from the injected `BoxReaderFactory`
(`box_reader_factory.py`) — this factory indirection exists so tests can inject
mock readers.

`BoxReader` (`box_reader.py`) does the real work in `read_jp2_file()`:
1. Reads bytes; validates via `jpylyzer.boxvalidator.BoxValidator`.
2. `check_boxes()` → `process_colr_box()` locates `colr` and computes
   `header_offset_position` from the `meth` byte (meth 1 → +7, meth 2 → +3;
   per ISO/IEC 15444-1:2019 Table I.11).
3. `process_all_trc_tags()` iterates `rTRC`/`gTRC`/`bTRC`, and
   `process_trc_tag()` compares the ICC tag size against the computed curv
   field length, rewriting the size bytes in a mutable `bytearray` copy when
   they differ and `n == 1`.
4. `write_modified_file()` writes a `*_modified_<YYYYMMDD>.jp2` sibling file
   only if bytes changed.

Every operation returns a `Jp2Result` (`jp2_result.py`), which carries
`is_empty`, `is_valid`, `curv_trc_gamma_n`, and `modified_file_path`, and
exposes `result_code()` (1=empty, 2=invalid, 3=skipped/unexpected n, 0=no
change, 4=remediated) and `is_skip_remediation()` (true when `n` is set and
`!= 1`). The "skip when n != 1" decision spans three files — `BoxReader` sets
`curv_trc_gamma_n`, `Jp2Result` interprets it, and `Processor` acts on it to
decide whether to upload to S3.

`InMemoryBoxReader` (`in_memory_box_reader.py`) subclasses `BoxReader` for
library consumers that pass image bytes directly; `remediate_jp2()` returns
`(Jp2Result, bytearray)` and writes nothing to disk. It is not used by the CLI.

The remediation logic is heavily commented with the exact ICC.1:2022 /
ISO/IEC 15444-1:2019 table references — preserve these when editing byte-offset
math.

## Environment variables

- Logging (`__init__.py:configure_logger`): `APP_LOG_LEVEL` (default `WARNING`),
  `LOG_DIR` (default `logs/`), `CONSOLE_LOGGING_ONLY` (default `true`; set
  `false` to also write a rotating file log), `LOG_FILE_BACKUP_COUNT` (default 30).
- S3 subcommand uses standard AWS credentials (`AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) from the environment.
- Publishing to PyPI: `UV_PUBLISH_USERNAME` and `UV_PUBLISH_PASSWORD` in `.env`, then `uv build && uv publish`.

## Docker

- Build: `./bin/docker-build.sh` (tags `artifactory.huit.harvard.edu/lts/jp2_remediator`)
- Run as executable: `./bin/docker-run.sh <args>` (bind-mounts CWD at `/data`)

## CI

`.github/workflows/pytest.yml` runs on push/PR: `flake8 ./src` then coverage
over the unit tests on Python 3.13, and publishes a coverage badge to an orphan
`badges/test-coverage` branch. flake8 config in `.flake8` (max line length 79).

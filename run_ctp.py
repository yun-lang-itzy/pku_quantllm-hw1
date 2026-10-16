#!/usr/bin/env python3
"""Local CTP demo entry: --setup installs; --verify checks; default streams ticks."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parent
DEMO_DIR = ROOT / 'experiments' / '002-ctp-demo'
VENV_DIR = ROOT / '.venv'


def python_path() -> Path:
    return VENV_DIR / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def prepare_config() -> bool:
    """Create a private template once; preserve existing account configuration."""
    target = DEMO_DIR / 'config.local.json'
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, 'wb') as output:
        output.write((DEMO_DIR / 'config.example.json').read_bytes())
    return True


def verify() -> int:
    interpreter = python_path()
    if not interpreter.is_file():
        print('Virtual environment missing. Run: python run_ctp.py --setup', flush=True)
        return 1
    code = (
        'import sys; sys.path.insert(0, sys.argv[1]); import demo; '
        'md, td = demo.load_native_api(); '
        'print("MdApi:", md().getApiVersion()); '
        'print("TdApi:", td().getApiVersion()); '
        'print("Native API ready; no network connection was started.")'
    )
    return subprocess.run([str(interpreter), '-c', code, str(DEMO_DIR)], cwd=ROOT).returncode


def setup() -> int:
    print(f'Preparing local environment: {VENV_DIR}', flush=True)
    if not python_path().is_file():
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    interpreter = python_path()
    source = ROOT / 'raw' / 'sources' / 'vnpy_ctp'
    command = [str(interpreter), '-m', 'pip', 'install', '--no-deps']
    if source.is_dir():
        work = ROOT / 'work'
        work.mkdir(exist_ok=True)
        # Build only a disposable copy; never generate files in the raw snapshot.
        with tempfile.TemporaryDirectory(prefix='ctp-build-', dir=work) as temporary:
            build = Path(temporary) / 'vnpy_ctp'
            shutil.copytree(source, build, symlinks=True)
            subprocess.run(command + [str(build)], cwd=ROOT, check=True)
    else:
        subprocess.run(command + ['-r', str(DEMO_DIR / 'requirements.txt')], cwd=ROOT, check=True)
    if prepare_config():
        print(f'Created {DEMO_DIR / "config.local.json"}. Fill in your SIMNOW credentials before running.', flush=True)
    else:
        print('Existing config.local.json preserved.', flush=True)
    return verify()


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if sys.version_info < (3, 10):
        print('Python 3.10 or newer is required.', file=sys.stderr)
        return 1
    try:
        if arguments == ['--setup']:
            return setup()
        if arguments == ['--verify']:
            return verify()
        if '--setup' in arguments or '--verify' in arguments:
            print('Use --setup or --verify alone; other arguments are forwarded to the demo.', file=sys.stderr)
            return 2
        if arguments in (['--help'], ['-h']):
            print('Local setup: python run_ctp.py --setup\nCheck native API: python run_ctp.py --verify\nStream ticks: python run_ctp.py\n', flush=True)
            return subprocess.run([sys.executable, str(DEMO_DIR / 'demo.py'), '--help'], cwd=ROOT).returncode
        interpreter = python_path()
        if not interpreter.is_file():
            print('Run python run_ctp.py --setup first.', file=sys.stderr)
            return 1
        if prepare_config():
            print(f'Fill in {DEMO_DIR / "config.local.json"}, then run again.', file=sys.stderr)
            return 1
        return subprocess.run([str(interpreter), '-u', str(DEMO_DIR / 'demo.py'), *arguments], cwd=ROOT).returncode
    except KeyboardInterrupt:
        return 130
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f'Local setup/run failed ({type(exc).__name__}): {exc}', file=sys.stderr)
        print('Source installation needs a C++ toolchain. See LOCAL_RUN.md.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

import argparse
import os
import sys
from pathlib import Path


def _bootstrap_paths() -> None:
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    candidates = [
        project_root / '.venv' / 'Lib' / 'site-packages',
        project_root / 'venv' / 'Lib' / 'site-packages',
    ]
    for py_site in (project_root / '.venv' / 'lib').glob('python*/site-packages'):
        candidates.append(py_site)
    for py_site in (project_root / 'venv' / 'lib').glob('python*/site-packages'):
        candidates.append(py_site)

    for path in candidates:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def main() -> None:
    parser = argparse.ArgumentParser(description='Launcher do sidecar FastAPI do CorretorIA')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--settings-path', default='data/desktop_settings.json')
    args = parser.parse_args()

    os.environ.setdefault('HOST', args.host)
    os.environ.setdefault('PORT', str(args.port))
    os.environ.setdefault('DESKTOP_SETTINGS_PATH', args.settings_path)

    _bootstrap_paths()

    import uvicorn

    uvicorn.run('app.main:app', host=os.getenv('HOST', args.host), port=int(os.getenv('PORT', str(args.port))))


if __name__ == '__main__':
    main()

# Desktop workspace

Este diretório contém a primeira versão da aplicação desktop do CorretorIA.

## Estrutura
- `frontend/`: interface React + Vite.
- `src-tauri/`: shell Tauri v2.
- `sidecar/launcher.py`: launcher do backend Python/FastAPI.
- `scripts/build_sidecar.ps1`: build do sidecar com PyInstaller one-folder.

## Desenvolvimento local
1. `cd desktop/frontend`
2. `npm install`
3. `npm run dev`

A UI fala com `http://127.0.0.1:8000` por padrão.

## Build desktop
- Requer Rust + Tauri CLI.
- Requer Python 3.12 para o sidecar empacotado, por causa do ChromaDB.
- Depois de gerar o sidecar com `desktop/scripts/build_sidecar.ps1`, a app Tauri passa a conseguir iniciar o backend embutido.

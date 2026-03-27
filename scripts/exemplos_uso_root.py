"""Backward-compatible entrypoint for knowledge-base examples."""

from scripts.exemplos_uso import *  # noqa: F401,F403


if __name__ == "__main__":
    from scripts.exemplos_uso import main

    main()

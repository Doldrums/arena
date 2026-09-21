"""Invoke EvoSkill's verified console entrypoint only during explicit execution."""


def main():
    # pyproject.toml at the recipe pin declares this exact entrypoint.
    from src.cli.main import cli
    return cli()


if __name__ == "__main__":
    raise SystemExit(main())

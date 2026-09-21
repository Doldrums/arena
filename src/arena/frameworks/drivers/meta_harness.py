"""Run the installed Harbor CLI against the pinned Meta-Harness artifact."""
from importlib.metadata import entry_points


def main():
    entries = tuple(entry_points(group="console_scripts", name="harbor"))
    if len(entries) != 1:
        raise RuntimeError("Exactly one installed Harbor console entrypoint is required")
    # Resolving the installed entrypoint avoids assuming an unverified Harbor
    # module path. Its version/dependencies remain part of the native environment.
    return entries[0].load()()


if __name__ == "__main__":
    raise SystemExit(main())

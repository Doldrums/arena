"""Run EvoPrompt GA/DE with environment-only API credentials."""
import copy
import os
from pathlib import Path
import runpy
import sys


def main(argv=None):
    import llm_client
    original_read = llm_client.read_yaml_file
    key = os.environ["OPENAI_API_KEY"]
    def read_auth(path):
        data = copy.deepcopy(original_read(path))
        for model in data.values():
            if isinstance(model, dict):
                for configuration in model.values():
                    if isinstance(configuration, dict) and "api_key" in configuration:
                        configuration["api_key"] = key
        return data
    llm_client.read_yaml_file = read_auth
    entrypoint = Path.cwd() / "run.py"
    sys.argv = [str(entrypoint), *(sys.argv[1:] if argv is None else argv)]
    try:
        runpy.run_path(str(entrypoint), run_name="__main__")
    finally:
        llm_client.read_yaml_file = original_read
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

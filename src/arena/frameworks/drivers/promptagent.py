"""Run PromptAgent's native search, avoiding its plaintext credential logging."""
import argparse
import copy
import os
from pathlib import Path
import runpy
import sys

from ._specialized import output_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    import yaml
    config = yaml.safe_load(Path(args.config).read_text())
    for role, environment_name in (("base", "PROMPTAGENT_BASE_API_KEY"),
                                    ("optim", "PROMPTAGENT_OPTIM_API_KEY")):
        settings = config[f"{role}_model_setting"]
        if settings.get("api_key"):
            raise ValueError("Use environment credentials, not keys inside the config")
        if settings["model_type"] in {"openai", "palm"}:
            settings["api_key"] = os.environ.get(environment_name) or os.environ["OPENAI_API_KEY"]
    config["log_dir"] = str(output_directory(args.output))
    sys.path.insert(0, str(Path.cwd() / "src"))
    namespace = runpy.run_path(str(Path.cwd() / "src/main.py"))
    namespace["validate_config"](config)
    native_agent = namespace["BaseAgent"]
    class EnvironmentCredentialAgent(native_agent):
        def log_vars(self):
            # The native method prints both complete model settings, including
            # credentials. Only this logging operation is redacted; search,
            # world model, task evaluation and model construction stay native.
            for name, value in vars(self).items():
                if name == "logger":
                    continue
                if name in {"base_model_setting", "optim_model_setting"}:
                    value = copy.copy(value)
                    value["api_key"] = "<environment>" if value.get("api_key") else None
                self.logger.info(f"{name} : {value}")
    EnvironmentCredentialAgent(**config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

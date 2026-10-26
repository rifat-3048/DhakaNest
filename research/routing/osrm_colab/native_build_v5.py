"""V8 targeted Sol2 build and explicit smoke-only readiness; bulk stays disabled."""

import argparse
import json
from pathlib import Path

from . import native_build_v3 as base
from .compatibility_v2 import POLICY, WARNING_HOOK, overrides, summarize_log, verify_compile_commands
from .storage import copy_once, sha
from .workflow import read, HERE


class Workflow(base.Workflow):
    def __init__(self, config):
        config = dict(config)
        self.authorize_runtime_smoke = config.pop("authorize_runtime_smoke", False)
        if type(self.authorize_runtime_smoke) is not bool:
            raise ValueError("authorize_runtime_smoke must be boolean")
        config["compatibility_policy_sha256"] = sha(POLICY)
        super().__init__(config)

    def command(self, command, stage, timeout=7200):
        if "research.routing.osrm_colab.build_v3" not in command:
            return super().command(command, stage, timeout)
        command = ["research.routing.osrm_colab.build_v5" if part == "research.routing.osrm_colab.build_v3" else part
                   for part in command]
        attempt = Path(command[command.index("--attempt") + 1])
        before = set(self.work.glob("setup-*.log"))
        try:
            result = super().command(command, stage, timeout)
            override = read(attempt / "build-override.json")
            if (override["policy_sha256"] != sha(POLICY) or override["warning_overrides"] != overrides(override["compiler_major"])
                    or override["warning_hook_sha256"] != sha(WARNING_HOOK)
                    or override["inherited_warning_hook_sha256"] != sha(HERE / "gcc11_compat.cmake")):
                raise ValueError("Unapproved Sol2 compatibility override")
            result["compatibility"] = verify_compile_commands(attempt / "build/compile_commands.json",
                                                              override["compiler_major"], attempt / "source")
            return result
        finally:
            for log in sorted(set(self.work.glob("setup-*.log")) - before):
                diagnostic = summarize_log(log.read_text(errors="replace"))
                diagnostic["warning_policy"] = read(POLICY)["warning_policy"]
                diagnostic["allowed_source_exceptions"] = read(POLICY)["warning_overrides"]
                self.record(f"{log.stem}.compatibility-diagnostics.json", {"log_sha256": sha(log), "diagnostics": diagnostic})
            patch = attempt / "coordinate-cstdint.patch"
            if patch.is_file():
                copy_once(patch, self.drive / "native_attempts" / attempt.name / patch.name)

    def runtime_smoke(self):
        """Only an explicitly approved later runtime test may process maps/start a server."""
        if self.authorize_runtime_smoke is not True or self.repair_only:
            raise RuntimeError("Runtime smoke not authorized: separately approve map preprocessing/server/Table test, set authorize_runtime_smoke=True and repair_only=False")

        def action():
            # Existing sequential extraction/partition/customize must all exit successfully.
            self.preprocess()
            try:
                self.server()
                plan = self.route_plan()
                validation = self.smoke(plan)
                return {"identity": self.identity(), "validation": validation,
                        "preprocess_sha256": sha(self.evidence / "preprocess.json"),
                        "smoke_sha256": sha(self.evidence / "smoke.json"),
                        "checks": ["extract", "partition", "customize", "server", "table"],
                        "bulk_acquisition_authorized": False}
            finally:
                self.stop_server()

        result = self.stage("runtime-smoke", action)
        if (result["identity"] != self.identity()
                or result["preprocess_sha256"] != sha(self.evidence / "preprocess.json")
                or result["smoke_sha256"] != sha(self.evidence / "smoke.json")):
            raise ValueError("Runtime readiness evidence changed; do not acquire routes")
        return result

    def acquire_and_finalize(self):
        raise RuntimeError("V8 repair never authorizes bulk acquisition. First obtain successful runtime-smoke evidence, then request separate routing approval/implementation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inputs", "runtime", "setup", "download", "preprocess", "runtime-smoke", "acquire", "offline"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    workflow = Workflow(read(args.config))
    method = {"acquire": workflow.acquire_and_finalize, "runtime-smoke": workflow.runtime_smoke}.get(
        args.stage, getattr(workflow, args.stage.replace("-", "_"), None))
    value = method()
    if value is not None:
        print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

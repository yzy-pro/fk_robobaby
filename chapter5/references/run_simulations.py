#!/usr/bin/env python3
"""Reproduce the selected chapter 5 tests without writing to the FPGA project.

Run from any directory. Requires Python 3, iverilog and vvp on PATH.
The default evidence directory is beside this script; binaries use /tmp.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

CASES = [
    ("imu_protocol", {}),
    ("attitude_cdc", {}),
    ("pose_async_fifo", {}),
    ("pose_ddr_arbiter", {"STREAM": 1}),
    ("pose_inverse_project_q14", {}),
    ("adaptive_gamma_stream", {}),
    ("pc_control", {}),
    ("gamma_telemetry", {"COLOR": 1}),
    ("pc_control_frame_alignment", {"GAMMA": 1}),
    ("rgb888_raster", {}),
    ("pose_renderer_tiled", {"WIDTH": 144, "HEIGHT": 40,
                             "TILE_W": 128, "TILE_H": 32}),
]
TRACES = {
    "attitude_cdc": "src_clk dst_clk src_rstn dst_rstn sy sp sr toggle dy dp dr valid",
    "pose_ddr_arbiter": "clk axi_awvalid axi_awready axi_awlen axi_wready axi_wlast write_beat_index cap_w_done render_w_done protocol_error",
}


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path,
                        default=here.parents[2] / "Pgl50h")
    parser.add_argument("--output", type=Path, default=here / "local_20261025")
    args = parser.parse_args()
    project, output = args.project.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    compiler, runtime = shutil.which("iverilog"), shutil.which("vvp")
    if not compiler or not runtime:
        parser.error("iverilog and vvp must be installed")
    directories = ["imu", "control", "video/pose", "video/preprocess",
                   "video/format", "video/timing"]
    sources = sorted(p for d in directories for p in (project / "src" / d).glob("*.v"))
    inputs = sources + [project / "tests" / ("tb_" + name + ".sv") for name, _ in CASES]
    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "project": str(project),
        "tool_version": subprocess.run([compiler, "-V"], capture_output=True,
                                       text=True).stdout.splitlines()[0],
        "sha256": {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in inputs},
        "cases": [],
    }
    with tempfile.TemporaryDirectory(prefix="chapter5_rtl_") as scratch:
        scratch = Path(scratch)
        for name, parameters in CASES:
            top = "tb_" + name
            executable = scratch / (name + ".vvp")
            command = [compiler, "-g2012", "-s", top, "-o", str(executable)]
            command += [f"-P{top}.{k}={v}" for k, v in parameters.items()]
            command += [str(project / "tests" / (top + ".sv"))]
            command += list(map(str, sources))
            if name in TRACES:
                trace = output / (name + "_trace.sv")
                signals = ", ".join(top + "." + s for s in TRACES[name].split())
                trace.write_text("module chapter5_trace;\ninitial begin\n"
                                 f'$dumpfile("{name}.vcd");\n'
                                 f"$dumpvars(0, {signals});\nend\nendmodule\n")
                command += ["-s", "chapter5_trace", str(trace)]
            print("Running " + name, flush=True)
            start = time.monotonic()
            compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
            (output / (name + ".compile.log")).write_text(compiled.stdout + compiled.stderr)
            result = None
            if compiled.returncode == 0:
                result = subprocess.run([runtime, str(executable)], cwd=output,
                                        capture_output=True, text=True, timeout=300)
                log = result.stdout + result.stderr
            else:
                log = "Compilation failed; see compile log.\n"
            (output / (name + ".log")).write_text(log)
            passed = (result is not None and result.returncode == 0
                      and "PASS" in log and not re.search(r"FATAL|ERROR", log))
            record = dict(name=name, parameters=parameters, compile_command=command,
                          run_command=[runtime, str(executable)],
                          compile_returncode=compiled.returncode,
                          run_returncode=None if result is None else result.returncode,
                          elapsed_seconds=round(time.monotonic() - start, 3),
                          passed=passed,
                          result_lines=[s for s in log.splitlines()
                                        if "PASS" in s or "MEASURE" in s])
            manifest["cases"].append(record)
            (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print("\n".join(record["result_lines"]) or log, flush=True)
            if not passed:
                raise SystemExit(name + " failed; evidence retained in " + str(output))
    print(f"PASS selected chapter 5 regression: {len(CASES)} cases", flush=True)


if __name__ == "__main__":
    main()

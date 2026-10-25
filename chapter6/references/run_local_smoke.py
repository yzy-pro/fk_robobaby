"""Run explicit supplemental RTL checks with Icarus; not a full-frame throughput test."""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build_rebuilt/pds_local20261025_pds2022_final/smoke'
BIN = Path('C:/FPGA/sim-tools-3ed4e67e733844cabede75db6445b403/iverilog/app/bin')

def main():
    OUT.mkdir(exist_ok=True)
    pose = [ROOT / 'src/video/pose' / name for name in (
        'pose_inverse_project_q14.v', 'pose_reciprocal_lut.v', 'pose_renderer_dma.v',
        'pose_renderer_tiled.v', 'pose_async_fifo.v', 'pose_ddr_arbiter.v', 'fram_buf_pose.v')]
    pose += [ROOT / 'src/video/preprocess' / name for name in ('adaptive_gamma_stream.v', 'adaptive_gamma_lut.v')]
    pose += [ROOT / 'src/video/format/rgb888_to_rgb565.v', ROOT / 'src/imu/imu_affine_q14.v']
    cases = [
        ('input_frame_alignment', None, [ROOT / 'src/video/format/rgb888_to_rgb565.v', ROOT / 'src/video/frame_buffer/wr_buf.v']),
        ('rgb888_raster', None, [ROOT / 'src/video/format/rgb565_to_rgb888.v', ROOT / 'src/video/timing/video_raster_delay.v']),
        ('pose_capture_throughput', None, pose),
        ('pose_renderer_tiled', {'WIDTH': 144, 'HEIGHT': 40}, pose),
    ]
    results = []
    for label, parameters, sources in cases:
        top = 'tb_' + label
        exe = OUT / (label + '.vvp')
        command = [str(BIN / 'iverilog.exe'), '-g2012', '-s', top, '-o', str(exe)]
        for key, value in (parameters or {}).items():
            command += ['-P' + top + '.' + key + '=' + str(value)]
        command += [str(ROOT / 'tests' / (top + '.sv')), *map(str, sources)]
        start = time.monotonic()
        result = subprocess.run(command, cwd=OUT, capture_output=True, text=True)
        (OUT / (label + '_compile.log')).write_text(result.stdout + result.stderr)
        record = {'label': label, 'parameter_overrides': parameters, 'compile_exit': result.returncode, 'passed': False}
        print('RUN', label, parameters, flush=True)
        if result.returncode == 0:
            try:
                result = subprocess.run([str(BIN / 'vvp.exe'), str(exe)], cwd=OUT, capture_output=True, text=True, timeout=180)
                output = result.stdout + result.stderr
                record.update(exit_code=result.returncode, passed=result.returncode == 0 and 'PASS' in output)
            except subprocess.TimeoutExpired as error:
                output = (error.stdout or b'').decode(errors='replace') if isinstance(error.stdout, bytes) else (error.stdout or '')
                record['timeout_seconds'] = 180
            (OUT / (label + '.log')).write_text(output)
            print(output[-2400:], flush=True)
        record['elapsed_seconds'] = time.monotonic() - start
        results.append(record)
        (OUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(json.dumps(record), flush=True)
    raise SystemExit(0 if all(r['passed'] for r in results) else 1)

if __name__ == '__main__':
    main()

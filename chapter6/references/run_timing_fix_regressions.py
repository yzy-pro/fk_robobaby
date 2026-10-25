"""Check display-tail scheduling and all added sampling pipeline alignment."""
import hashlib
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build_rebuilt/timing_fix_20261025_sim'
BIN=Path('C:/FPGA/sim-tools-3ed4e67e733844cabede75db6445b403/iverilog/app/bin')

def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--concurrent-only',action='store_true')
    args=parser.parse_args()
    if args.concurrent_only:
        OUT=OUT/'runtime_integration'
    OUT.mkdir(parents=True,exist_ok=True)
    pose=[ROOT/'src/video/pose'/n for n in ('pose_inverse_project_q14.v','pose_reciprocal_lut.v',
        'pose_renderer_dma.v','pose_renderer_tiled.v','pose_async_fifo.v','pose_ddr_arbiter.v','fram_buf_pose.v')]
    pose += [ROOT/'src/video/preprocess'/n for n in ('adaptive_gamma_stream.v','adaptive_gamma_lut.v')]
    pose += [ROOT/'src/video/format/rgb888_to_rgb565.v', ROOT/'src/imu/imu_affine_q14.v']
    cases=[
        ('arbiter','tb_pose_ddr_arbiter',{},[ROOT/'src/video/pose/pose_ddr_arbiter.v']),
        ('arbiter_stream','tb_pose_ddr_arbiter',{'STREAM':1},[ROOT/'src/video/pose/pose_ddr_arbiter.v']),
        ('display_tail_wrapper','tb_fram_buf_pose',{},pose),
        ('tile_edges','tb_pose_renderer_tiled',{'WIDTH':144,'HEIGHT':40},pose),
        ('tile_runtime_identity','tb_pose_renderer_tiled',{'WIDTH':144,'HEIGHT':40,'RUNTIME':1,'CONTROL_MODE':0},pose),
        ('tile_runtime_lens','tb_pose_renderer_tiled',{'WIDTH':144,'HEIGHT':40,'RUNTIME':1,'CONTROL_MODE':1},pose),
        ('capture','tb_pose_capture_throughput',{},pose),
        ('tiled320x180','tb_pose_renderer_tiled',{},pose),
        ('concurrent','tb_fram_buf_pose_tiled',{'H':160,'V':96,'FRAMES':28,'SHARED_PAYLOAD':1,'REFRESH_CYCLES':35,'PREPROCESS':1,'RUNTIME':1},pose),
    ]
    manifest={'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in pose},'cases':[]}
    if args.concurrent_only:
        cases=[c for c in cases if c[0]=='concurrent']
    for label,top,overrides,sources in cases:
        start=time.monotonic()
        exe=OUT/(label+'.vvp')
        command=[str(BIN/'iverilog.exe'),'-g2012','-s',top,'-o',str(exe)]
        for k,v in overrides.items():command+=['-P'+top+'.'+k+'='+str(v)]
        command += [str(ROOT/'tests'/(top+'.sv')),*map(str,sources)]
        result=subprocess.run(command,cwd=OUT,capture_output=True,text=True)
        (OUT/(label+'_compile.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        print('RUN',label,overrides,flush=True)
        with (OUT/(label+'.log')).open('w') as log:
            result=subprocess.run([str(BIN/'vvp.exe'),str(exe)],cwd=OUT,stdout=log,stderr=subprocess.STDOUT,timeout=2400)
        output=(OUT/(label+'.log')).read_text(errors='replace')
        record={'label':label,'overrides':overrides,'exit_code':result.returncode,'passed':result.returncode==0 and 'PASS' in output and 'FATAL' not in output,'elapsed_seconds':time.monotonic()-start}
        manifest['cases'].append(record)
        (OUT/'results.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(output[-2500:],flush=True)
        print(json.dumps(record),flush=True)
        if not record['passed']:raise SystemExit(1)
    print('PASS all timing-fix RTL regressions',flush=True)

if __name__=='__main__':main()

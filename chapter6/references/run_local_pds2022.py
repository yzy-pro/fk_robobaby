"""Build final immutable RTL with installed PDS2022; preserve original XML project."""
import hashlib
import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build_rebuilt/pds_local20261025_pds2022_final'
SHELL=Path('C:/pango/PDS_2022.2-SP3/bin/pds_shell.exe')
TEMPLATE=Path('C:/FPGA/test/test.pds')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--timing-fix',action='store_true')
    args=parser.parse_args()
    if args.output:
        OUT=(ROOT/args.output).resolve()
    if ROOT/'build_rebuilt' not in OUT.parents:
        raise SystemExit('Build output must be inside build_rebuilt')
    if OUT.exists(): raise SystemExit('Refusing to replace existing build')
    OUT.mkdir(parents=True)
    original=ROOT/'EmbFPGA.pds'
    tree=ET.parse(original)
    sources=[]
    for item in tree.iter('item'):
        name=item.get('file','')
        if item.get('type')=='FILE' and name.startswith('src/') and name.endswith(('.v','.vp')):
            sources.append(name)
    # PDS2022 uses explicit IP RTL instead of the newer XML IP registration.
    sources += ['ipcore/video_pll/pll.v',
      'ipcore/wr_fram_buf/wr_fram_buf.v',
      'ipcore/wr_fram_buf/rtl/ipml_sdpram_v1_10_wr_fram_buf.v',
      'ipcore/rd_fram_buf/rd_fram_buf.v',
      'ipcore/rd_fram_buf/rtl/ipml_sdpram_v1_10_rd_fram_buf.v']
    ddr=ROOT/'ipcore/DDR3_50H'
    sources += sorted(p.relative_to(ROOT).as_posix() for p in (ddr/'rtl').rglob('*') if p.suffix in ('.v','.vp'))
    sources += ['ipcore/DDR3_50H/DDR3_50H.v','ipcore/DDR3_50H/DDR3_50H_ddrphy_top.v']
    assert len(sources)==len(set(sources))
    for name in sources+['src/constraints/hdmi_ddr3_top.fdc']:
        assert (ROOT/name).is_file(),name
    for name in ('src','ipcore'): shutil.copytree(ROOT/name,OUT/'input_snapshot'/name)
    shutil.copy2(original,OUT/'input_snapshot/original_project.pds')
    shutil.copy2(TEMPLATE,OUT/'input_snapshot/pds2022_template.pds')
    hashes={p.relative_to(OUT/'input_snapshot').as_posix():digest(p)
            for name in ('src','ipcore') for p in (OUT/'input_snapshot'/name).rglob('*') if p.is_file()}
    expected=json.loads((ROOT/'verification/pds_timing_review_20261024/snapshot_identity.json').read_text())['source_files']
    different=[p for p in set(hashes)|set(expected) if hashes.get(p)!=expected.get(p)]
    allowed={'src/video/pose/fram_buf_pose.v','src/video/pose/pose_renderer_tiled.v'}
    assert (set(different)==allowed if args.timing_fix else not different),different
    project=TEMPLATE.read_text(encoding='utf-8')
    entries=[]
    for name in sources:
        top=' + "hdmi_ddr3_top"' if name=='src/top/hdmi_ddr3_top.v' else ''
        entries.append('                (_file "input_snapshot/'+name+'"'+top+'\n                    (_format verilog)\n                )')
    block='        (_widget wgt_my_design_src\n            (_input\n'+'\n'.join(entries)+'\n            )\n        )'
    project,n=re.subn(r'(?ms)^        \(_widget wgt_my_design_src\r?\n        \)',lambda m:block,project)
    assert n==1
    block='        (_widget wgt_import_logic_con_file\n            (_input\n                (_file "input_snapshot/src/constraints/hdmi_ddr3_top.fdc"\n                    (_format fdc)\n                )\n            )\n        )'
    project,n=re.subn(r'(?ms)^        \(_widget wgt_import_logic_con_file\r?\n        \)',lambda m:block,project)
    assert n==1
    project=re.sub(r'(?ms)^    \(_project\s*.*?^    \)','    (_project\n    )',project)
    project=project.replace('(_gci_state (_integer 4))','(_gci_state (_integer 0))')
    project=project.replace('(_option selected_syn_tool_opt (_integer 1))','(_option ads (_switch ON))\n            (_option selected_syn_tool_opt (_integer 2))')
    project=project.replace('(_command cmd_compile','(_command cmd_compile\n            (_option top_module (_string "hdmi_ddr3_top"))')
    project=project.replace('(_command cmd_pnr','(_command cmd_pnr\n'+ '\n'.join('            (_option '+o+' (_switch ON))' for o in ('optimize_multi_corner_timing','fix_hold_violation','optimize_gp_recovery','optimize_dp_recovery','optimize_rp_recovery'))+'\n            (_option max_hold_violated_paths_num (_integer 50000))')
    project=project.replace('(_command cmd_report_post_pnr_timing','(_command cmd_report_post_pnr_timing\n            (_option report_max_skew (_switch ON))\n            (_option max_path (_integer 64))\n            (_option nworst (_integer 64))')
    nl=chr(10)
    stamp=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    for fmt in ('verilog','fdc'):
        project=project.replace('(_format '+fmt+')','(_format '+fmt+')'+nl+'                    (_timespec "'+stamp+'")')
    target=OUT/'EmbFPGA_pds2022.pds'
    target.write_text(project,encoding='utf-8')
    record={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'tool':str(SHELL),'tool_version':'PDS2022.2-SP3',
      'started_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
      'original_project_sha256':digest(original),'adapter_project_sha256':digest(target),
      'template_sha256':digest(TEMPLATE),'explicit_rtl_count':len(sources),
      'active_sources':sources,'source_files':hashes,
      'conversion':'XML2025 to native PDS2022 project wrapper; explicit IP RTL, same device and unchanged FDC; multi-corner/hold/skew settings enabled',
      'source_matches_archived_final':not different,
      'changes_from_archived_final':{p:{'before_sha256':expected.get(p),'after_sha256':hashes.get(p)} for p in sorted(different)},
      'timing_fix':args.timing_fix,'board_tested':False}
    (OUT/'local_input_identity.json').write_text(json.dumps(record,indent=2)+'\n')
    print('START native PDS2022 full flow:',target,flush=True)
    print('Snapshot inputs:',len(hashes),'explicit RTL:',len(sources),flush=True)
    start=time.monotonic()
    with (OUT/'full_build.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([str(SHELL),'-project',str(target),'-run','gen_bit_stream','-work_dir',str(OUT)],cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
    changed=[p for p,h in hashes.items() if digest(ROOT/p)!=h or digest(OUT/'input_snapshot'/p)!=h]
    result_record={'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,
      'finished_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
      'source_changes':changed,'full_build_passed':False,'board_tested':False}
    text=(OUT/'full_build.log').read_text(errors='replace')
    result_record['tool_errors']=re.findall(r'^E:.*$',text,re.M)
    (OUT/'local_build_result.json').write_text(json.dumps(result_record,indent=2)+'\n')
    print(json.dumps(result_record,indent=2),flush=True)
    if result.returncode or changed or result_record['tool_errors']:raise SystemExit(1)

if __name__=='__main__':main()

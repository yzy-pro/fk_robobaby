"""Audit this report's actual local build, including failures, without changing RTL."""
import hashlib
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build_rebuilt/pds_local20261025_pds2022_final'
ARCHIVE = ROOT / 'verification/local_build_20261025'
DOMAINS = {'sys_clk', 'pixclk_in', 'pixel_clk', 'cfg_clk', 'ddrphy_clkin', 'ioclk0', 'ioclk1'}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')

def main():
    global BUILD, ARCHIVE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path)
    parser.add_argument('--archive-dir',type=Path)
    parser.add_argument('--archive',action='store_true')
    parser.add_argument('--timing-fix',action='store_true')
    args=parser.parse_args()
    if args.build: BUILD=(ROOT/args.build).resolve()
    if args.archive_dir: ARCHIVE=(ROOT/args.archive_dir).resolve()
    identity = json.loads((BUILD / 'local_input_identity.json').read_text())
    result_file = BUILD / 'local_build_result.json'
    process = json.loads(result_file.read_text()) if result_file.is_file() else {
        'exit_code': None, 'tool_errors': [], 'state': 'running', 'full_build_passed': False}
    raw = BUILD / 'report_timing/rtr.db'
    root = ET.parse(raw).getroot()
    tables = {t.attrib['id']: t for t in root.findall('table') if 'id' in t.attrib}
    out = BUILD / 'report_timing/report_db'
    out.mkdir(exist_ok=True)
    for name, table in tables.items():
        doc = ET.Element('report')
        doc.append(table)
        ET.ElementTree(doc).write(out / (name + '.db'), encoding='utf-8', xml_declaration=True)
    def rows(name):
        return [[n.text or '' for n in row.findall('data')] for row in tables[name].findall('row')]
    timing = {'numeric_timing_passed': False, 'summaries': {}, 'violations': [], 'coverage_errors': []}
    for corner in ('slow', 'fast'):
        for kind in ('setup', 'hold', 'recovery', 'removal', 'mpw'):
            name = corner + '_' + kind
            entries = rows('report_timing_' + name)
            if not entries:
                timing['coverage_errors'].append('Empty ' + name)
            for entry in entries:
                slack, total = map(float, entry[-4:-2])
                failing, endpoints = map(int, entry[-2:])
                if not (math.isfinite(slack) and math.isfinite(total) and slack >= 0 and total == 0 and failing == 0 and endpoints > 0):
                    timing['violations'].append({'check': name, 'row': entry})
            if kind in ('setup', 'hold'):
                covered = {e[0] for e in entries if e[0] == e[1]}
                missing = sorted(DOMAINS - covered)
                if missing:
                    timing['coverage_errors'].append({'check': name, 'missing_domains': missing})
                if not any(e[:2] == ['pixel_clk', 'pixclk_out_clk'] for e in entries):
                    timing['coverage_errors'].append('Missing HDMI output ' + name)
            timing['summaries'][name] = {'minimum_slack_ns': min((float(e[-4]) for e in entries), default=None), 'rows': entries}
    timing['checks'] = {e[0]: int(e[1]) for e in rows('check_timing_summary')}
    for name in ('no_clock', 'unexpandable_clocks', 'partial_input_delay', 'partial_output_delay', 'io_min_max_delay_consistency', 'input_delay_assigned_to_clock', 'loops', 'latch_loops', 'latchs'):
        if timing['checks'].get(name) != 0:
            timing['coverage_errors'].append({'structural_check': name, 'value': timing['checks'].get(name)})
    timing['numeric_timing_passed'] = not (timing['violations'] or timing['coverage_errors'])
    sys.path.insert(0, str(ROOT / 'tools'))
    from audit_pose_fifo_cdc import audit
    try:
        cdc = audit(out)
        cdc['passed'] = True
    except (ValueError, OSError, ET.ParseError) as error:
        cdc = {'passed': False, 'error': str(error)}
    changed = [p for p, h in identity['source_files'].items() if sha(ROOT / p) != h or sha(BUILD / 'input_snapshot' / p) != h]
    snr = (BUILD / 'synthesize/hdmi_ddr3_top.snr').read_text(errors='replace')
    prr = (BUILD / 'place_route/hdmi_ddr3_top.prr').read_text(errors='replace')
    resource_rows = [[v.strip() for v in line.split('|')[1:]] for line in prr.splitlines() if line.startswith('|')]
    def physical(label):
        return [float(r[1]) for r in resource_rows if r[0] == label]
    synthesis = {}
    for name in ('LUT', 'Register', 'APM', 'DRM'):
        matches = [line for line in snr.splitlines() if name in line]
        synthesis[name + '_raw_lines'] = matches[:12]
    def numeric(pattern):
        match = re.search(pattern, snr)
        if not match:
            raise ValueError('Missing synthesis resource: ' + pattern)
        return float(match.group(1))
    synthesis_values = {
        'lut': int(numeric(r'Total LUTs: (\d+)')),
        'ff': int(numeric(r'Total Registers: (\d+)')),
        'apm': numeric(r'Total APMs = ([\d.]+)'),
        'drm_equivalent': numeric(r'Total DRM18K = ([\d.]+)'),
        'distributed_ram_lut': int(numeric(r'LUTs as dram: (\d+)')),
        'latches': int(numeric(r'Total Latches: (\d+)')),
    }
    bitstreams = sorted((BUILD / 'generate_bitstream').glob('*.sbit'))
    result = {
        'tool': identity['tool_version'], 'source_commit': identity['source_commit'],
        'source_file_count': len(identity['source_files']), 'source_changes': changed,
        'process': process, 'timing_passed': timing['numeric_timing_passed'],
        'cdc_passed': cdc['passed'],
        'synthesis_resources': synthesis_values,
        'routed_resources': {'lut': sum(physical('LUT')), 'ff': sum(physical('FF')), 'apm': physical('Use of APM')[0], 'drm_equivalent': physical('Use of DRM')[0]},
        'synthesis_raw': synthesis,
        'generated_bitstreams': [{'path': p.relative_to(BUILD).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in bitstreams],
        'full_build_passed': process['exit_code'] == 0 and not process['tool_errors'] and not changed and bool(bitstreams) and timing['numeric_timing_passed'] and cdc['passed'],
        'board_tested': False, 'recommended_for_board_programming': False,
    }
    dump(BUILD / 'numeric_timing.json', timing)
    dump(BUILD / 'pose_fifo_cdc.json', cdc)
    dump(BUILD / 'local_validation.json', result)
    original_logs = ROOT / 'build_rebuilt/rtl_a48f35a2721e4ee28b75f7abd1a98045'
    passed_cases = [p.stem for p in original_logs.glob('*.log') if 'PASS' in p.read_text(errors='replace') and 'FATAL' not in p.read_text(errors='replace')]
    retry = (BUILD / 'tile_retry.log').read_text(errors='replace') if not args.timing_fix else ''
    smoke = json.loads((BUILD / 'smoke/results.json').read_text()) if not args.timing_fix else []
    simulations = json.loads((ROOT/'build_rebuilt/timing_fix_20261025_sim/results.json').read_text()) if args.timing_fix else {
        'initial_runner': {'completed': False, 'reason': 'Icarus tiled test exceeded original 90 second wall timeout', 'passed_cases': passed_cases},
        'tiled_320x180_rerun': {'passed': 'PASS tiled renderer' in retry and 'FATAL' not in retry, 'same_compiled_testbench': True, 'five_poses': True, 'not_1080p_throughput': True},
        'supplemental': smoke, 'full_1080p_rerun': False, 'post_route_simulation': False,
    }
    if args.timing_fix:
        simulations['superseded_cases']=[dict(c,reason='Stopped intentionally; replaced by 160x96 28-frame shared-DDR runtime integration') for c in simulations['cases'] if c['label']=='concurrent']
        simulations['cases']=[c for c in simulations['cases'] if c['label']!='concurrent']
        runtime_results=ROOT/'build_rebuilt/timing_fix_20261025_sim/runtime_integration/results.json'
        if runtime_results.is_file():
            runtime=json.loads(runtime_results.read_text())
            if runtime['source_sha256']!=simulations['source_sha256']:
                raise ValueError('Runtime integration sources differ')
            simulations['cases'].extend(runtime['cases'])
        simulation_source_changes=[p for p,h in simulations['source_sha256'].items() if sha(ROOT/p)!=h]
        result['simulation_source_changes']=simulation_source_changes
        result['functional_regression_passed']=len(simulations['cases'])==9 and all(c['passed'] for c in simulations['cases']) and not simulation_source_changes
        result['full_build_passed']=result['full_build_passed'] and result['functional_regression_passed']
        result['timing_fix']=True
        result.pop('recommended_for_board_programming',None)
        result['recommended_for_board_test']=result['full_build_passed']
        result['qualification']='timing_and_RTL_passed_board_unverified' if result['full_build_passed'] else 'not_qualified'
        result['changes_from_archived_final']=identity['changes_from_archived_final']
        dump(BUILD/'local_validation.json',result)
    dump(BUILD / 'local_simulation.json', simulations)
    if args.archive:
        ARCHIVE.mkdir(exist_ok=True)
        selected = [
            'full_build.log', 'local_input_identity.json', 'local_build_result.json',
            'local_validation.json', 'numeric_timing.json', 'pose_fifo_cdc.json', 'EmbFPGA_pds2022.pds',
            'local_simulation.json', 'local_rtl_regression.log', 'tile_retry.log', 'local_smoke.log',
            'synthesize/hdmi_ddr3_top.snr', 'synthesize/run.log',
            'place_route/hdmi_ddr3_top.prr', 'place_route/hdmi_ddr3_top_timing_summary_after_hold_fix.txt',
            'report_timing/rtr.db', 'report_timing/run.log',
        ]
        selected += [p.relative_to(BUILD).as_posix() for p in (BUILD / 'report_timing').glob('*.rtr')]
        selected += [p.relative_to(BUILD).as_posix() for p in bitstreams]
        selected += [p.relative_to(BUILD).as_posix() for p in (BUILD / 'smoke').glob('*') if p.suffix in ('.log', '.json')]
        for name in selected:
            src = BUILD / name
            if src.is_file():
                dst = ARCHIVE / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        if args.timing_fix:
            for src in (ROOT/'build_rebuilt/timing_fix_20261025_sim').glob('*'):
                if src.suffix in ('.log','.json'):
                    dst=ARCHIVE/'simulation'/src.name
                    dst.parent.mkdir(exist_ok=True)
                    shutil.copy2(src,dst)
            for src in (ROOT/'build_rebuilt/timing_fix_20261025_sim/runtime_integration').glob('*'):
                if src.suffix in ('.log','.json'):
                    dst=ARCHIVE/'simulation/runtime_integration'/src.name
                    dst.parent.mkdir(exist_ok=True)
                    shutil.copy2(src,dst)
            patch=ROOT/'build_rebuilt/timing_fix_20261025_sim/fix.patch'
            if patch.is_file(): shutil.copy2(patch,ARCHIVE/'fix.patch')
            for name in list(identity['changes_from_archived_final'])+['src/constraints/hdmi_ddr3_top.fdc']:
                dst=ARCHIVE/'verified_sources'/name
                dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/name,dst)
        else:
            for label in passed_cases:
                dst = ARCHIVE / 'initial_regression' / (label + '.log')
                dst.parent.mkdir(exist_ok=True)
                shutil.copy2(original_logs / (label + '.log'), dst)
        worst = []
        for row in tables['report_timing_slow_path_setup'].findall('row'):
            fields = [n.text or '' for n in row.findall('data')]
            if float(fields[0]) < 0:
                worst.append(fields)
        dump(ARCHIVE / 'negative_setup_paths.json', worst)
        manifest = {p.relative_to(ARCHIVE).as_posix(): sha(p) for p in ARCHIVE.rglob('*') if p.is_file() and p.name != 'evidence_sha256.json'}
        dump(ARCHIVE / 'evidence_sha256.json', manifest)
    print(json.dumps({k: v for k, v in result.items() if k != 'synthesis_raw'}, indent=2))
    print('Timing minima:', {k: v['minimum_slack_ns'] for k, v in timing['summaries'].items()})
    print('Timing violations:', timing['violations'])
    print('Coverage:', timing['coverage_errors'])
    print('Checks:', timing['checks'])
    print('CDC passed:', cdc['passed'])

if __name__ == '__main__':
    main()

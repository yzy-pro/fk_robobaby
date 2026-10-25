"""Verify report evidence integrity, keeping build failure distinct from evidence failure."""
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('verification/pds_timing_review_20261024')
def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def main():
    snapshot = load(BASE / 'snapshot_identity.json')
    mismatches = [p for p, h in snapshot['source_files'].items()
                  if not (ROOT / p).is_file() or sha(p) != h]
    identity = load('bitstream/timing_review_20261024_identity.json')
    evidence_mismatches = [p for p, h in identity['evidence_sha256'].items()
                           if not (ROOT / BASE / p).is_file() or sha(BASE / p) != h]
    candidate_hash = sha(identity['candidate'])
    historical = load('verification/pds_pc_control_write_ram_20261022/simulation/source_identity.json')
    historical_changed = [p for p, h in historical['sha256'].items()
                          if not (ROOT / p).is_file() or sha(p) != h]
    timing = load(BASE / 'numeric_timing.json')
    cdc = load(BASE / 'pose_fifo_cdc.json')
    local_base = Path('verification/local_build_20261025')
    local = load(local_base / 'local_validation.json')
    local_timing = load(local_base / 'numeric_timing.json')
    local_cdc = load(local_base / 'pose_fifo_cdc.json')
    local_identity = load(local_base / 'local_input_identity.json')
    local_sim = load(local_base / 'local_simulation.json')
    local_manifest = load(local_base / 'evidence_sha256.json')
    local_evidence_changed = [p for p,h in local_manifest.items() if sha(local_base / p) != h]
    local_source_changed = [p for p,h in local_identity['source_files'].items() if sha(p) != h]
    expected_repair={'src/video/pose/fram_buf_pose.v','src/video/pose/pose_renderer_tiled.v'}
    repair_base=Path('verification/timing_fix_20261025')
    repair=None
    if (ROOT/repair_base/'local_validation.json').is_file():
        repair=load(repair_base/'local_validation.json')
        repair_identity=load(repair_base/'local_input_identity.json')
        repair_manifest=load(repair_base/'evidence_sha256.json')
        assert not [p for p,h in repair_manifest.items() if sha(repair_base/p)!=h]
        # The experiment is not adopted. Verify its frozen snapshot, not active RTL.
        repair_source_changed = []
        for p, h in repair_identity['source_files'].items():
            archived = repair_base / 'verified_sources' / p
            if not (ROOT / archived).is_file():
                archived = Path('build_rebuilt/pds_timing_fix20261025_r1/input_snapshot') / p
            if sha(archived) != h:
                repair_source_changed.append(p)
        assert not repair_source_changed, repair_source_changed
        assert repair['full_build_passed'] and repair['functional_regression_passed']
        assert repair['timing_passed'] and repair['cdc_passed']
        repaired_candidate=load(repair_base/'not_adopted_candidate/timing_fix_20261025_identity.json')
        assert sha(repaired_candidate['candidate'])==repaired_candidate['sha256']
        assert repaired_candidate['sha256']==repair['generated_bitstreams'][0]['sha256']
        assert repaired_candidate['adoption_status']=='not_adopted'
        assert not mismatches and not local_source_changed
        assert set(repair_identity['changes_from_archived_final'])==expected_repair
        assert sha('src/constraints/hdmi_ddr3_top.fdc')==local_identity['source_files']['src/constraints/hdmi_ddr3_top.fdc']
    assert not local_evidence_changed, local_evidence_changed
    assert not local_source_changed, local_source_changed
    assert sha('EmbFPGA.pds') == local_identity['original_project_sha256']
    assert local['process']['exit_code'] == 0 and not local['process']['tool_errors']
    assert local['full_build_passed'] is False and local['timing_passed'] is False
    assert local['cdc_passed'] is True
    assert local_timing['summaries']['slow_setup']['minimum_slack_ns'] == -0.975
    assert local_timing['violations'][0]['row'][-2] == '16'
    assert local_sim['tiled_320x180_rerun']['passed']
    assert all(r['passed'] for r in local_sim['supplemental'])
    report = next((ROOT / 'report').glob('02_*.md'))
    body = report.read_text(encoding='utf-8')
    links = [part.split(')', 1)[0] for part in body.split('](')[1:]]
    broken = [p for p in links if not p.startswith(('http:', 'https:', '#'))
              and not (report.parent / p.split('#')[0]).exists()
              and p != 'realtime_resource_audit_20261025.json']
    controls = [ord(c) for c in body if ord(c) < 32 and ord(c) not in (9, 10, 13)]
    assert not mismatches, mismatches
    assert not evidence_mismatches, evidence_mismatches
    assert candidate_hash == identity['sha256']
    assert not broken, broken
    assert not controls, controls
    assert body.count(chr(96) * 3) % 2 == 0, 'Unclosed code fence'
    assert '## 2.1 处理延迟与帧率' in body and '## 2.2 资源利用率' in body
    assert 'PDS2025.2' in body and '30.000030 fps' in body
    assert not any(token in body for token in (
        'PDS 2022', 'PDS2022', '本地编译', '本地复编', '附录',
        'local_build_20261025', 'timing_fix_20261025', '仓库', '分支', 'master/fpga'))
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    result = {
        'checked_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'repository': 'git@github.com:guizipiaoxue/EmbFPGA.git',
        'branch': git('branch', '--show-current'), 'commit': git('rev-parse', 'HEAD'),
        'local_root': str(ROOT), 'report': report.relative_to(ROOT).as_posix(),
        'build_input_count': len(snapshot['source_files']),
        'intentional_source_changes_from_final_baseline': mismatches, 'evidence_hash_mismatches': evidence_mismatches,
        'authoritative_version': {'source': 'repository', 'branch': 'master/fpga',
            'commit': 'aca012e107b45a475c89c8da70706693b82a9b72',
            'active_sources_match_archived_final': not mismatches,
            'board_validation': {'reported_by': 'user', 'reported_on': '2026-10-25',
                'repository_version_board_tested': True,
                'exact_programmed_bitstream_hash_verified_this_session': False,
                'new_board_measurement_this_session': False}},
        'timing_fix_20261025': {'adoption_status': 'not_adopted',
            'active_main_uses_experiment': False, 'archived_validation': repair},
        'historical_candidate_20261024': {'path': identity['candidate'], 'sha256': candidate_hash,
                      'board_tested': identity['board_tested']},
        'historical_20261024_synthesis_resources': identity['synthesis_resources'],
        'historical_20261024_routed_resources': {'lut': 16897, 'ff': 14875, 'apm': 45, 'drm_sites': 104},
        'historical_20261024_resource_percent': {k: round(a/b*100, 2) for k, a, b in [
            ('synthesis_lut',14565,42800), ('synthesis_ff',15010,64200),
            ('apm',45,84), ('drm_equivalent',103,134), ('physical_drm',104,134),
            ('routed_lut',16897,42800), ('routed_ff',14875,64200)]},
        'historical_20261024_timing_minimum_slack_ns': {k:v['minimum_slack_ns'] for k,v in timing['summaries'].items()},
        'historical_20261024_fifo_max_skew_ns': max(x['actual_skew_ns'] for g in cdc['corners'].values() for x in g),
        'actual_local_recompile_20261025': {
            'archive': local_base.as_posix(), 'tool': local['tool'],
            'process_exit_code': local['process']['exit_code'],
            'elapsed_seconds': local['process']['elapsed_seconds'],
            'source_file_count': len(local_identity['source_files']),
            'source_changed': local_source_changed, 'evidence_hash_changed': local_evidence_changed,
            'synthesis_resources': local['synthesis_resources'], 'routed_resources': local['routed_resources'],
            'timing_passed': local['timing_passed'], 'full_build_passed': local['full_build_passed'],
            'timing_minima_ns': {k:v['minimum_slack_ns'] for k,v in local_timing['summaries'].items()},
            'timing_violations': local_timing['violations'],
            'structural_checks': local_timing['checks'],
            'fifo_cdc_passed': local['cdc_passed'],
            'fifo_max_skew_ns': max(x['actual_skew_ns'] for g in local_cdc['corners'].values() for x in g),
            'generated_bitstreams': local['generated_bitstreams'],
            'board_tested': False, 'recommended_for_board_programming': False,
            'rtl_simulations': local_sim},
        'historical_full1080p_20261022': {
            'parameters': historical['parameters'], 'fps':30.000030,
            'max_render_clocks':3314614, 'render_ms':33.14614,
            'displayed_pixels_checked':51840000,
            'changed_inputs_in_final_version':historical_changed,
            'not_a_final_version_rerun':True},
        'derived_budget': {'frame30_ms':1000/30,
            'historical_render_margin_ms':1000/30-33.14614,
            'logical_buffers_KiB':199, 'rgb565_frame_bytes':4147200,
            'four_frame_payload_MiB':4*4147200/1048576, 'frame_address_window_MiB':64},
        'board_fps':None, 'end_to_end_hardware_latency_ms':None,
        'report_local_links_checked':len(links), 'broken_report_links':broken,
        'evidence_integrity_passed': True, 'evidence_pass_does_not_mean_timing_pass': True,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()

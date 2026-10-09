#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only Station 04 integrity + UTF-8 + deterministic path validator."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.request import urlopen

REQUIRED = (
    'frontend/home/index.html', 'frontend/viber/index.html',
    'backend/main.py', 'data/viber_takeover_scenario.json',
    'static/css/viber.css', 'static/css/home-station04.css',
    'static/js/viber.js', 'tests/test_viber_station.py',
)
VARIANTS = ('sms', 'flash_call')
OUTCOMES = {'danger', 'safe', 'best_safe'}
EXPECTED = {
    'chat_opening', 'small_favor', 'wrong_number_pretext', 'pretext_reassure',
    'verification_dispatch', 'verification_sms', 'verification_flash_call',
    'verification_request', 'pressure_after_refusal', 'pressure_after_verification',
    'final_decision', 'end_danger', 'end_safe', 'end_best_safe',
}
PROTECTED = (
    'data/call_scenarios.json', 'data/sms_scenarios.json', 'data/qr_scenarios.json',
    'static/js/call.js', 'static/js/sms.js', 'static/js/qr.js',
    'static/css/call.css', 'static/css/sms.css', 'static/css/qr.css',
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root: Path, http_base: str | None = None) -> int:
    errors = []
    passes = []

    def ok(message):
        passes.append(message)
        print('PASS:', message)

    def require(cond, message):
        if cond:
            ok(message)
        else:
            errors.append(message)
            print('FAIL:', message)

    for rel in REQUIRED:
        require((root / rel).is_file(), rel + ' exists')
    if errors:
        print('NOT READY: missing required files')
        return 1

    for rel in REQUIRED:
        path = root / rel
        try:
            content = path.read_text(encoding='utf-8-sig')
            require('\ufffd' not in content and '????' not in content and
                    not any(mark in content for mark in ('Î“', 'Ïƒ', 'ÃŽ', 'Ã\x8e')),
                    rel + ' UTF-8/mojibake')
        except UnicodeError:
            require(False, rel + ' UTF-8')

    data = json.loads((root / 'data/viber_takeover_scenario.json').read_text(encoding='utf-8'))
    nodes = data['nodes']
    require(set(nodes) == EXPECTED, 'exactly 14 approved scenario nodes')
    require(data['start_node'] == 'chat_opening', 'start node')
    require(tuple(data['variants']) == VARIANTS, 'SMS and Flash Call variants')
    require(data['default_variant'] == 'sms', 'SMS default variant')
    require(set(data['endings']) == OUTCOMES, 'exactly three approved endings (no CAUTION)')
    require(all(isinstance(data['endings'][out]['sections'], list) and
                len(data['endings'][out]['sections']) == 3 for out in OUTCOMES),
            'three learning sections per ending')
    require('εναλλακτική επαφή' in nodes['pretext_reassure']['messages'][0]['text'],
            'approved Greek pretext present')
    require('Δεν σου στέλνω τίποτα. Θα επιβεβαιώσω πρώτα ότι είσαι εσύ με άλλο τρόπο και τα ξαναλέμε.' ==
            nodes['final_decision']['choices'][1]['text'], 'locked SAFE answer intact')
    require('Σταματάμε εδώ. Σε παίρνω τώρα τηλέφωνο στο νούμερο που έχω αποθηκευμένο.' ==
            nodes['final_decision']['choices'][2]['text'], 'locked BEST SAFE answer intact')
    require([c['id'] for c in nodes['final_decision']['choices']] == ['A', 'B', 'C'],
            'final choice labels A/B/C')
    require([c['id'] for c in nodes['verification_request']['choices']] == ['A', 'B', 'C'],
            'request choice labels A/B/C')

    path_counts = Counter()
    path_errors = []
    expected_variants = {'sms': 'verification_sms', 'flash_call': 'verification_flash_call'}
    require(nodes['verification_dispatch']['next_by_variant'] == expected_variants,
            'dispatch routes correct')
    require(nodes['verification_request']['choices'][0]['next_node'] == 'end_danger',
            'early disclosure reaches DANGER')
    require(nodes['final_decision']['choices'][0]['next_node'] == 'end_danger' and
            nodes['final_decision']['choices'][1]['next_node'] == 'end_safe' and
            nodes['final_decision']['choices'][2]['next_node'] == 'end_best_safe',
            'final outcomes correctly linked')
    visited_all = set()
    for variant in VARIANTS:
        paths = [(data['start_node'], tuple())]
        completed = 0
        while paths:
            node_id, history = paths.pop()
            if node_id not in nodes:
                path_errors.append('missing node ' + node_id)
                continue
            if node_id in history or len(history) > 30:
                path_errors.append('loop detected at ' + node_id)
                continue
            visited_all.add(node_id)
            node = nodes[node_id]
            seen = history + (node_id,)
            if 'outcome' in node:
                outcome = node['outcome']
                if outcome not in OUTCOMES:
                    path_errors.append('unexpected ending ' + outcome)
                path_counts[(variant, outcome)] += 1
                completed += 1
            elif 'choices' in node:
                for choice in node['choices']:
                    if 'text' not in choice and variant not in choice.get('text_by_variant', {}):
                        path_errors.append('missing choice label in ' + node_id)
                    paths.append((choice['next_node'], seen))
            elif 'next_by_variant' in node:
                paths.append((node['next_by_variant'][variant], seen))
            elif 'next_node' in node:
                paths.append((node['next_node'], seen))
            else:
                path_errors.append('dead end ' + node_id)
            if completed > 1000:
                path_errors.append('too many paths')
                break
    require(not path_errors, 'all node links terminate without loops/dead ends')
    require(visited_all == set(nodes), 'no unreachable nodes')
    require(all(path_counts[(variant, out)] > 0 for variant in VARIANTS for out in OUTCOMES),
            'all three endings reachable in both variants')
    require('caution' not in json.dumps(data).lower(), 'no CAUTION outcome')
    print('Deterministic terminal paths:', dict(sorted(path_counts.items())))

    home = (root / 'frontend/home/index.html').read_text(encoding='utf-8')
    backend = (root / 'backend/main.py').read_text(encoding='utf-8')
    html = (root / 'frontend/viber/index.html').read_text(encoding='utf-8')
    require(home.count('href="/viber"') == 1, 'one home station 04 entry')
    require('home-station04.css' in home, 'home layout stylesheet present')
    require('station04-enabled' in home, 'home 4-station layout activated')
    require('def get_viber_scenario()' in backend and '@app.get("/api/viber-scenario")' in backend,
            'isolated backend data endpoint')
    require('@app.get("/viber")' in backend, 'isolated backend page route')
    require('/static/js/viber.js' in html and '/static/css/viber.css' in html,
            'new UI loads only new station assets')
    try:
        ast.parse(backend)
        ok('backend Python syntax')
    except SyntaxError as ex:
        require(False, f'backend Python syntax: {ex}')
    if shutil.which('node'):
        p = subprocess.run(['node', '--check', str(root / 'static/js/viber.js')], capture_output=True, text=True)
        require(p.returncode == 0, 'Viber JavaScript syntax (node --check)')

    manifest_path = root / '.fraudlab_station04_install.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for rel, expected_sha in manifest['protected'].items():
            require((root / rel).exists() and sha(root / rel) == expected_sha,
                    'untouched legacy asset: ' + rel)
        for rel, expected_sha in manifest['deployed'].items():
            require((root / rel).exists() and sha(root / rel) == expected_sha,
                    'installed Station 04 integrity: ' + rel)
    else:
        print('INFO: no installation manifest; legacy file hashes cannot be compared')

    if http_base:
        host = http_base.rstrip('/')
        for route in ('/', '/viber', '/api/viber-scenario', '/api/health', '/call', '/sms', '/qr', '/api/sms-challenge', '/api/qr-challenge'):
            try:
                with urlopen(host + route, timeout=5) as response:
                    payload = response.read()
                    require(response.status == 200 and len(payload) > 0, 'HTTP ' + route)
            except Exception as ex:
                require(False, 'HTTP ' + route + ': ' + str(ex))

    print(f'\nStation 04 validation: {len(passes)} PASS, {len(errors)} FAIL')
    print('EXHIBITION READY (Station 04)' if not errors else 'NOT READY (Station 04)')
    return 0 if not errors else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--http-base', default=None, help='Optional running local URL, e.g. http://127.0.0.1:8000')
    args = parser.parse_args()
    sys.exit(check(args.root.resolve(), args.http_base))

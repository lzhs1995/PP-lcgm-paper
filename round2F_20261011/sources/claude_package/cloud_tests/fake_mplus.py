#!/usr/bin/env python3
"""云端假 Mplus：按 model.inp 的规格从 Round2E 合成冒烟输出复制 model.out/estimates.dat/tech3.dat，
并按输入里的 LOGCRITERION/RLOGCRITERION 改写输出中打印的收敛准则（模拟 Mplus 回显）。
环境变量 FAKE_MODE=ignore_criteria 时不改写；FAKE_MODE=reject 时写出 *** ERROR。只用于云端演练。"""
import os, re, shutil, sys
from pathlib import Path
inp = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
r2e = Path(os.environ['FAKE_R2E']) / 'models'
mode = os.environ.get('FAKE_MODE', '')
if mode == 'reject':
    Path('model.out').write_text('*** ERROR in ANALYSIS command\n  Unknown option: LOGCRITERION\n', encoding='utf-8'); sys.exit(0)
spec = 'E0' if 'XWITH' not in inp else ('E1B' if re.search(r'^sy@0;', inp, re.M) else 'E1')
src = r2e / {'E0': 'SYNTHETIC_SD_E0_01_smoke', 'E1': 'SYNTHETIC_SD_E1_01_smoke', 'E1B': 'SYNTHETIC_SD_E1B_01_smoke'}[spec]
for f in ('estimates.dat', 'tech3.dat'):
    shutil.copy(src / f, f)
out = (src / 'model.out').read_text(encoding='latin-1')
if mode != 'ignore_criteria':
    for opt, label in (('LOGCRITERION', 'Loglikelihood change'), ('RLOGCRITERION', 'Relative loglikelihood change')):
        m = re.search(r'(?<![A-Z])' + opt + r'=([0-9.]+);', inp)
        if m:
            v = float(m.group(1)); e = int(f'{v:e}'.split('e')[1]) + 1
            out = re.sub(r'(\n\s*' + label + r'\s+)[0-9.]+D[-+][0-9]+', lambda g: g.group(1) + f'0.100D{e:+03d}'.replace('+', '+'), out, count=1)
Path('model.out').write_text(out, encoding='latin-1', newline='')

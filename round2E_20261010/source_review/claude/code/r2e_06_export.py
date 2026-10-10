"""Round2E 回传包：只收白名单文件；不收 private/、data.dat 或任何个人级数据。只用标准库。
用法：python -I r2e_06_export.py <R2E_ROOT> <输出zip路径> [<code目录>]
"""
import hashlib, json, os, sys, zipfile

KEEP_MODEL = {'model.inp', 'model.out', 'estimates.dat', 'tech3.dat', 'receipt.json', 'input_contract.json', 'start_mapping.csv',
              'key_paths.csv', 'key_printed_comparison.csv', 'parameters_high_precision.csv', 'parameter_covariance.csv', 'gate.json',
              'geometry.json', 'process.json', 'resource_before.json', 'mplus_console.log', 'extraction_error.json', 'key_error.json'}
TOP = ('contracts', 'audit', 'runtime', 'results')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    root, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    code = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else None
    if os.path.exists(out):
        sys.exit('output exists; choose a new name')
    files = []
    for top in TOP:
        for d, _, fs in os.walk(os.path.join(root, top)):
            for f in fs:
                if f.endswith('.dat') or f == 'PAUSE':
                    continue
                files.append(os.path.join(d, f))
    for d, _, fs in os.walk(os.path.join(root, 'models')):
        for f in fs:
            if f in KEEP_MODEL:
                files.append(os.path.join(d, f))
    rows = []
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            assert not rel.startswith('private/') and not rel.endswith('/data.dat'), rel
            z.write(p, 'round2E/' + rel)
            rows.append({'path': 'round2E/' + rel, 'bytes': os.path.getsize(p), 'sha256': sha(p)})
        if code:
            for f in sorted(os.listdir(code)):
                p = os.path.join(code, f)
                if os.path.isfile(p) and f.endswith(('.R', '.py')):
                    z.write(p, 'code/' + f)
                    rows.append({'path': 'code/' + f, 'bytes': os.path.getsize(p), 'sha256': sha(p)})
        z.writestr('MANIFEST_2E.json', json.dumps({'files': rows, 'count': len(rows),
                                                    'excluded': 'private/, every data.dat and other .dat except estimates/tech3, PAUSE'}, indent=1))
    print('EXPORT', out, len(rows), 'files')


if __name__ == '__main__':
    main()

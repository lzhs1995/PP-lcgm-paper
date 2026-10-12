"""Round2F 回传包：只收白名单文件；不收 private/、任何 data.dat、完整控制或截尾数据、SQLite 台账或任何个人级数据。只用标准库。
用法：python -I r2f_export.py <R2F_ROOT> <输出zip路径> [<code目录>]
"""
import hashlib, json, os, sys, zipfile

KEEP_MODEL = {'model.inp', 'model.out', 'estimates.dat', 'tech3.dat', 'receipt.json', 'engine_receipt.json', 'input_contract.json',
              'start_mapping.csv', 'key_paths.csv', 'matrix_values.csv', 'parameters_high_precision.csv', 'parameter_covariance.csv',
              'tech1_parameter_map.csv', 'gate.json', 'process.json', 'resource_before.json', 'mplus_console.log', 'engine_console.log',
              'exact_ll.json', 'extraction_error.json', 'key_error.json'}
TOP = ('contracts', 'audit', 'runtime', 'results')
SKIP_EXT = ('.dat', '.sqlite', '.sqlite-journal', '.sqlite-wal')
SKIP_NAME = {'KEEP_AWAKE_STOP', 'PAUSE'}


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
                if f.endswith(SKIP_EXT) or f in SKIP_NAME:
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
            assert not rel.startswith('private/') and not rel.endswith('/data.dat') and not rel.endswith('.sqlite'), rel
            z.write(p, 'round2F/' + rel)
            rows.append({'path': 'round2F/' + rel, 'bytes': os.path.getsize(p), 'sha256': sha(p)})
        if code:
            for f in sorted(os.listdir(code)):
                p = os.path.join(code, f)
                if os.path.isfile(p) and f.endswith(('.R', '.py', '.ps1')):
                    z.write(p, 'code/' + f)
                    rows.append({'path': 'code/' + f, 'bytes': os.path.getsize(p), 'sha256': sha(p)})
        z.writestr('MANIFEST_2F.json', json.dumps({'files': rows, 'count': len(rows),
                                                    'excluded': 'private/, every data.dat and other .dat except estimates/tech3, SQLite ledger, KEEP_AWAKE_STOP, PAUSE'}, indent=1))
    print('EXPORT', out, len(rows), 'files')


if __name__ == '__main__':
    main()

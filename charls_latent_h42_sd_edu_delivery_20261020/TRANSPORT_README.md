# CHARLS H4.2 SD×教育包：网络分片传输说明

当前 ZIP 在本机仍是完整的 `CHARLS_H42_SD_EDU_20261020.zip`（约 8.8 MB）。GitHub 代理对一次性大 blob 上传超时，因此公开目录同时提供 9 个 1,000,000 字节分片及 `PARTS_MANIFEST.json`。

按文件名中的 `part-01-of-09` 到 `part-09-of-09` 顺序拼接，即可恢复完整 ZIP。拼接完成后，必须核对 manifest 中的原始字节数和 SHA-256：

```powershell
$parts = Get-ChildItem .\transport_parts\*.part-* | Sort-Object Name
$out = [IO.File]::OpenWrite('.\CHARLS_H42_SD_EDU_20261020.zip')
try { foreach ($p in $parts) { $bytes = [IO.File]::ReadAllBytes($p.FullName); $out.Write($bytes, 0, $bytes.Length) } } finally { $out.Dispose() }
Get-FileHash .\CHARLS_H42_SD_EDU_20261020.zip -Algorithm SHA256
```

预期原始 SHA-256 是 `60cea1ff1723069f80ce67e3de7daaa314784f55721a1a7a533a31bf429f3f04`。分片只改变传输方式，不改变包内容；原始 ZIP 的内部 manifest 仍包含全部逐文件哈希。

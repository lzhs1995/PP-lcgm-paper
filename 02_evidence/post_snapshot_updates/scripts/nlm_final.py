"""对v45/v38冻结PDF对执行最终三审；历史v44目录保留。"""
import nlm_v44 as review
import sys

review.ROOT = review.OUT / 'reviews/v45_v38'
review.ROOT.mkdir(exist_ok=True)
review.PDF_RECEIPT = review.OUT / 'manuscript/final_pdf_receipt.json'
review.NOTEBOOK_TITLE = 'CFPS 七项意见标签核正最终候选 v45-v38 20261005'
if sys.argv[1] == 'upload':
    review.upload()
elif sys.argv[1] == '3':
    man=review.readj(review.ROOT/'source_manifest.json')
    ss=man['sources']
    for s in ss:
        assert review.sha(s['path'])==s['sha256']
    prompt=('全文第三审：['+ss[0]['filename']+']与['+ss[1]['filename']+']的标题、表注、符号、跨页表格、交叉引用和结论是否一致？不限于新增内容。请列出两份PDF各自的原文引证，尤其复核Process-4说明、Sibling指标标签与附录A.1—A.64的索引关系，再列其余全文问题；区分抽取伪影及已标注科学局限。600字内。末尾NEW_ISSUES_COUNT: N；A5_NO_NEW_ISSUES: YES或NO。')
    r=review.run_query(review.NLM,man['notebook_id'],prompt,[s['id'] for s in ss],review.ROOT/'pass3_full_concise',filename=ss[0]['filename'],profile='default',timeout=180,attempts=1)
    print('FINAL_REVIEW_3',r['status'],flush=True)
    if r['status']!='PASS':
        raise RuntimeError('最终第三审来源验证未通过')
else:
    review.query(int(sys.argv[1]), concise=True)

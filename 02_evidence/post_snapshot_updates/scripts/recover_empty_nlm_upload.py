"""仅清理本轮已核实为空的失败占位，保留回执后恢复同一PDF上传。"""
from review_workspace import OUT, readj, writej
from pathlib import Path
import nlm_v44 as review
import shutil, json

root=OUT/'reviews/v45_v38'
pre=readj(root/'upload_recovery_preflight.json')
assert pre['tls_http_status']==200 and pre['auth']['status']=='AUTH_VALID'
assert pre['rule_count']==1 and pre['group_count']==1
nb=readj(root/'notebook.json')['id']
sid='01de7f51-473c-4c11-be9b-40bd389b5460'
listed=json.loads(readj(root/'source_list_after_upload_failure.json')['stdout'])
assert any(s['id']==sid and s['title']=='PP_LGCM_appendix_review_v38_NOT_RELEASED.pdf' and s['status']==5 for s in listed)
details=json.loads(readj(root/'failed_source_details.json')['stdout'])
assert details['title']=='PP_LGCM_appendix_review_v38_NOT_RELEASED.pdf' and details['char_count']==0 and details['content']==''
old=root/'PP_LGCM_appendix_review_v38_NOT_RELEASED_upload_raw.json'
backup=root/'PP_LGCM_appendix_review_v38_NOT_RELEASED_upload_failed_ssl.json'
assert not backup.exists()
shutil.copy2(old,backup)
review.ROOT=root
review.PDF_RECEIPT=OUT/'manuscript/final_pdf_receipt.json'
review.NOTEBOOK_TITLE='CFPS 七项意见标签核正最终候选 v45-v38 20261005'
review.call('empty_source_delete', ['source','delete',sid,'--confirm','--json'])
print('EMPTY_PLACEHOLDER_REMOVED',sid,flush=True)
review.upload()

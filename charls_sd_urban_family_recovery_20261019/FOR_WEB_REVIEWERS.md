# 在线独立复核

将ZIP解压到同一目录。R中执行 source("verification/verify_pooled_base.R"); verify_pooled_base(getwd(), phase="EDU_URBAN", public=TRUE)，依赖jsonlite、digest。这独立读取20份原始保存参数与TECH3，并复算完整协方差、组间差和条件斜率。Python标准库执行 python verification/verify_twelve_recovery.py --public，核对旧11行未变和固定12项校正。

PAYLOAD_MANIFEST.json记录公开字节SHA及本地原字节SHA。路径脱敏不称原字节相同。新结果只补SD_URBAN，其他11项原输出请使用REPORT内的既有固定提交，不需重传。无逐人DAT/RDS/MIDS，不能宣称重新拟合或核对微观资料。本轮不启动新NLM。


## 版本2：图题与测量说明更正

本轮新增图的英文标题一度误写relative SD，现更正为absolute SD。CHARLS实际Z₀是基期子女见面频率的绝对标准差，不是除以均值的相对SD；CHARLS见面频率也不等于CFPS情感亲近度。此处仅修正展示及解释，所有输入、20份估计、TECH3、合并表和12项检验字节不变。原图代码和V1固定提交96ae3d30保留；修正程序见code/correct_plot_label.R和plot_recovered_v2.R。

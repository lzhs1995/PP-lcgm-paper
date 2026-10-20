# 本轮前台诊断异常与原会话恢复（2026-10-20 UTC）

本记录针对执行者自己提交的只读诊断，不是 Mplus 拟合失败。该诊断把 `ps::ps()` 全进程枚举和多个进程的 CPU/亲和性查询放进同步 `execute_r`，重复了现有 recovery-runbook 已提醒的前台扫描风险。这是本轮排查安排的失误，不应归咎于统计模型或数据。

1. 原生调用先返回 `R Error: HTTP error communicating with RStudio:`，外层 `isError:false`；后续短调用报告 Addin 未运行。Windows HTTP 备用的短调用也超时。不能用这些消息推断 R 或异步作业已退出。
2. 定向 Windows `OpenProcess`/`GetExitCodeProcess` 显示 RStudio 8764、另一个受保护会话18112和本批worker1740/9456仍存活，TCP8787仍能连接。独立监控保存Mplus PID、CPU增长、物理/commit余量。后台模型继续从既有job推进，无新提交。
3. 通过 RStudio父进程、可执行路径和 HWND 验证，定位属于8764的桌面窗口。`GetProcessTimes`核验原创建时间。先向该窗口投递一次Escape消息，只有“消息已投递”的证据，没有宣称恢复。
4. 随后仅临时恢复并获取该窗口，确认 `GetForegroundWindow()==target` 后发送 Ctrl+2 与 Escape，中断范围限本执行者的已知只读前台诊断。随后恢复原最小化和前台窗口状态。没有终止R、worker或Mplus，没有改ClaudeR/bridge配置，也没有重启原会话。
5. 02:24:32 UTC的HTTP调用返回200和 `success:true`，实际输出 `POST_ESCAPE_HTTP 8764`。重新绑定已有default会话后，原生调用实际返回 `NATIVE_RECOVERY_CONFIRMED PID=8764`。
6. 原生同job轮询继续显示a2c6d44a执行SD MI17、48baa180执行gender MI20。恢复后的轮询仍使用原ID，既有结果不重跑。

这些观察证明同一会话恢复及后台作业继续存活。由于期间既有消息投递、实际控制台中断、时间经过和重新绑定，不能唯一声称某个动作单独导致恢复。系统存在2GiB以上物理余量和更多commit余量，也不能据此宣称内存耗尽是原因。

后续规则：常规诊断只查询已知句柄；广泛进程枚举放在有界外部诊断进程，带开始/结束时间和初始PID回执。原生前台只执行短表达式。HTTP失败后先核对本任务所有权、持久输出和实际后台作业，恢复绑定并轮询原job；不要重复提交或重启R。只有前台任务明确为自己提交的可中断诊断时，才可按PID/创建时间/窗口身份保护尝试中断；不能把本例推广到未知或正在计算的用户分析。

证据：audit/FOREGROUND_DIAGNOSTIC_HTTP_ERROR.json、RECOVERY_HTTP_02.json、TARGETED_RECOVERY_04.json、OWNED_RSTUDIO_UI.json、OWNED_FOREGROUND_INTERRUPT_INTENT.json、OWNED_FOREGROUND_INTERRUPT_POSTED.json、OWNED_CONSOLE_INTERRUPT_INTENT.json、OWNED_CONSOLE_INTERRUPT_ATTEMPT.json、RECOVERY_HTTP_AFTER_ESCAPE.json、NATIVE_RECOVERY_CONFIRMED.json，以及LIVE_RESOURCE.jsonl和两条PROGRESS日志。

PR60已合并的d931c3012b1c0aad9ed11e5c049c4c9e2f151003记录了之前已核实的Rterm身份、启动握手和求积校准；本记录属于之后发生的接续证据，不能谎称已包含在PR60。待本批实质交付时统一补入guide，避免每次轮询触发新PR/CI。本机托管安装状态也必须单列。

## 终态与耗时实测

两条原作业于03:23:11、03:25:27 UTC结束；原生终态均已实际消费，两个防休眠守卫的 completion 均为 stop_requested/released=true，所有权监控以 OWNERS_EXITED 结束。本批实际84次调用是80份主估计加4次起点检查，无重复提交。

现有阶段日志与84份引擎回执的只读计时汇总如下（本机 audit/PHASE_TIMING_AUDIT.json）：

|阶段|84次累计秒数|单次中位秒数|单次最大秒数|
|---|---:|---:|---:|
|编译与启动命令准备|268|3|11|
|runModels阶段（含包装器、准入、启动及引擎）|11713|137|188|
|结果读取|203|2|4|
|引擎清醒时间|11084.29|128.89|178.06|

第一条队列阶段墙钟6135秒，第二条6074秒；两队列并行，不能相加当作项目耗时。从第一条开始编译到最后一条结束合并共6271秒，约104.52分钟，不含先前完整案例校准、插补及后续独立复核/交付。阶段日志精度为1秒，引擎清醒时间剔除睡眠；两类计时不能直接相减后全归咎于某个程序。读回在本批只占很小部分，实际引擎估计仍是主要耗时。没有做受控性能基准，不能声称这些数据证明特定倍数加速、唯一CPU瓶颈或内存不足。

恢复后另有少数状态查询瞬时返回addin未运行；重读同一job又成功且进度增长。没有据此新增窗口中断、重启R或重提作业。这进一步说明接口读状态异常必须与后台估计状态分开判断，不代表该异常的唯一原因已查明。

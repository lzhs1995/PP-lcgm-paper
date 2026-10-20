# CHARLS H4.2 SD×教育：资源等待后恢复原规格

## 当前边界

四项调节完整推断、完整 H4 仍未完成。本批是 CHARLS 联系频率绝对 SD 的教育组差工作模型，不是 CFPS 相对亲近度模型；不得互换测量名称。原始目录与已完成模型未修改。

## 已核实的时间线（UTC）

- 2026-10-20 06:04:21：旧 job `dd2df6bb` 因物理余量 1.516 GiB 低于原合同 1.2+0.4 GiB 进入 NOT_RUN_RESOURCE_HOLD；实际引擎调用 0。已消费原生终态、关闭 guard、核实 worker 退出。
- 06:12:22：旧运行记录归档到 `recovery/first_resource_hold`。原模型输入和数据哈希不变，只生成新的启动 nonce、恢复脚本和新 job。模型目录仍无已执行结果，不覆盖任何成功估计。
- 06:15:59：宿主可用内存实测 2.438 GiB。保留原资源阈值、GH15、20 主成员+1 独立起点、每模型 240 清醒秒和总 5040 秒预算。
- 恢复提交获得真实 job `b4dbd705`；worker `29848`，创建时间 `1792477105.7242963`，父 RStudio `8764`。guard register 回执 `9d981f62-3533-46e6-b478-1deb9b372126`。
- 06:19:06：同 worker 启动检查完成，实测选用当时较空闲逻辑核 0、3、5、7；只改所属 worker 的亲和性。不将该核集合推广为固定规则。
- 06:21:24：MI01_A 可用；06:23:50：MI01_B 可用；06:23:59：进入 MI02_A，说明双起点比较已通过 runner 的冻结条件。独立全家族验证尚未运行。
- 期间原生 `get_async_result` 返回 `isError:false`、正文却为 “RStudio addin is not running”。只读进程证据同时确认 worker 存活、Mplus PID12304 的父链包含 29848→8764；不是模型失败，也不能据此重复提交。
- `list_sessions` 仍列出原 8787/8764 和 8789/18112。重新 `connect_session(default)` 后，原生 `get_async_result(b4dbd705)` 恢复，报告原 job 已运行 433 秒、阶段 MI02_A。未修改 ClaudeR 源码、配置或注册表。

## 没有效果的内存尝试

仅对当前代理自己的 tmux pane 保存可恢复屏幕记录后清理历史；其 history_bytes 和 tmux RSS 未显著下降。Windows 前后可用内存分别约 1.778、1.749 GiB，不能声称释放了 420 MiB，也不能将后续内存回升归因于该操作。其他 pane 和 R 会话未操作。屏幕存档在 `private_recovery`，可能包含私密信息，禁止公开发布。

## 沉淀到 guide 的规则

再次报同一接口错误后，本地桥接源码只读核查发现 `check_addin_status()` 先执行2秒GET，并将所有异常吞掉后返回False；调用方统一显示addin未运行。`connect_session` 对已引入的同一代理主要更新目标会话名。因此，后续轮询恢复不能单独证明“重新绑定修复了根因”；响应延迟、端点瞬时状态等仍需实测。没有对运行中的桥接打补丁，也没有把源码中的可能路径当成本次已证实的异常类型。

06:50:30—06:50:34 UTC 外部只读端点采样，超时设置依次为2、10、2、10秒，四次均HTTP200，耗时分别2.412、0.477、0.511、0.554秒，响应均213字节且SHA-256相同。这是urllib端点诊断，不能直接复现httpx的异常或证明2秒阈值是唯一原因；请求超时也不一定等于整个调用的墙钟上限。本地源码SHA-256为 `b202bcdf1eceedf60342701d67556a4c764a06fa5dce13e1f653ff19a9362930`，未对实际运行桥接进行注入或打点。原始记录保存在本地 `audit/HEALTH_LATENCY_DIAGNOSTIC.json`；本节保存可公开的测量摘要。

1. 接口错误和引擎状态分开检查；正文错误即使 `isError:false` 也要记录。
2. 对原 job 先检查 PID+创建时间+父链+持久化阶段，再只读诊断端点和重新绑定会话；活跃模型不得因轮询错误重提。
3. 资源未准入的 0 引擎任务单列 NOT_RUN，不计入统计失败或成功模型数。恢复前关闭旧 worker/guard，保全零调用证据，核对输入哈希。
4. 保留单一资源准入规则，不在 bootstrap 再加重复阈值；前一批额外 2 GiB 启动限制已证实阻塞了满足原合同的任务。
5. 子 worker 自行做归属检查，避免等待可能丢失的提交回执引起启动握手超时。
6. 内存优化须报告实测收益；缓存账面大小不代表可回收物理内存，失败尝试只记录，不不断重试。

本文件为实测案例源；PR61 已发布的通用恢复规则继续沿用。本批增量尚未发布到 guide，待有界家族终态后集中整理，避免每次轮询单独发布。

## 证据入口

`audit/RESOURCE_RESUME_PREPARED.json`、`audit/NATIVE_RESUME1_SUBMIT.json`、`audit/GUARD_RESUME1_REGISTER.json`、`audit/PREFLIGHT.json`、`audit/STATUS_RESUME1_001.json`、`audit/NATIVE_RESUME1_POLL_ERROR_001.json`、`audit/NATIVE_RESUME1_REBOUND_POLL.json`、`runtime/PROGRESS.jsonl`。HTTP 诊断单独标记 transport；不充当原生 MCP 成功证据。

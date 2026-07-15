# Accordance 应用目录

这里是项目的实际 Python 源码目录。

## 运行

```bash
python main.py
```

CLI 问事入口与 Web 使用相同的必填、长度和固定选项边界，不再用“未命名问题”等占位内容继续起卦。分析完成后先显示简短结论；只有明确输入 `y`、`yes` 或“是”才展开完整依据，直接回车默认返回菜单。

运行不写入正式历史的标准回归测试：

```bash
python -m unittest discover -s tests -v
```

测试功能时可临时重定向或禁用 CLI 历史，避免测试问题写入正式复问记录：

```powershell
$env:ACCORDANCE_HISTORY_FILE = "$PWD\.data\test_question_history.json"
python main.py

$env:ACCORDANCE_HISTORY_DISABLED = "1"
python main.py
```

## 移动端 Web

当前阶段按本机/同一局域网使用。电脑终端关闭、电脑休眠、断网或切换网络后，手机端会停止访问。

从项目根目录启动 Windows 脚本：

```powershell
.\start_local_web.ps1
```

也可以手动启动：

```bash
cd ..
python -m pip install -r requirements.txt
cd Accordance
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

同一 Wi-Fi 或同一手机热点下，手机访问 `http://电脑局域网IP:8000`。Web 版按匿名设备隔离历史记录，不需要注册登录；本机 Web 历史默认保存在 `Accordance/.data/web_clients/`，不会进入 GitHub。
需要凝神的问事入口会在浏览器和服务端同时校验默念步骤；资料变更后必须重新凝神，直接调用 API 也不能用零值绕过。
应用统一拒绝超过 64KB 的请求体，并设置禁止嵌入、同源内容策略及摄像头/麦克风/定位禁用头；即使不经过 Caddy 也保持相同边界。
匿名设备 Cookie 在本机 HTTP 下保持可用，经 HTTPS/Caddy 访问时自动增加 `Secure`，并始终限制为 HttpOnly、SameSite=Lax、全站路径。

云服务器、Docker/Caddy 和公网部署文件仍保留在仓库中，但当前不是必需步骤。

## 目录结构

```text
config/                    基础数据与规则
  bagua_data.py              八卦、八宫、体用生克象义
  bazi_data.py               八字十神、藏干、阶段与格局基础数据
  qimen_data.py              奇门九宫、八门、九星、八神、三奇六仪、六甲遁仪与场景规则
  hexagram_data.py            六十四卦全录（卦辞+爻辞+互错综映射）
  hexagram_calibration.py     六十四卦象义校准（主轴/宜用/风险）
  naja_data.py                京房纳甲、世应、六亲六神十二长生
  wuxing_rules.py             五行生克、天干地支、六冲六合、三合三会、刑冲合害
  daxiang_data.py             六十四卦大象传（《象传》）
  tuanzhuan_data.py           六十四卦彖传（《彖传》）      ← 新增
  shensha_data.py             神煞子系统（天乙贵人、文昌、驿马等）← 新增
  yijing_philosophy.py        人本哲学、卦德修养、吉凶处境建议
  traditional_sources.py      传统依据链、问类现实校验与实占边界

core/                    核心逻辑
  bazi.py                     四柱八字基础分析 + 大运流年 + 临界时辰对照
  qimen.py                    奇门运筹分析（方位/时机窗口/格局诊断/遁甲/主客矩阵/行动方案/执行闸门/综合裁决/置信度，简化九宫盘）
  divination.py               多种起卦法（时间/动态/姓名/三爻/日卦）
  zhuanggua.py                完整装卦引擎 + 卦身 + 进神退神 + 反吟伏吟
  interpretation.py           综合解卦（纳甲+体用+用神+彖传+卦身+神煞+简短结论）
  qi_context.py               气机计算（精确日干支、旬空、月建、时干支）
  question_history.py         问题历史（持久化 + 中文语义去重 + 分层拦截 + 记录压缩）
  method_selector.py          起卦法选择器
  rule_audit.py               纳甲/世应/卦象校准/选择器一致性审计
  question_precheck.py        起卦前问事校准（问类/用神/方法边界）

modules/                 功能模块
  bazi.py                     八字基础分析 CLI
  qimen.py                    奇门运筹 CLI
  full_divination.py          六爻详占
  quick_divination.py         三爻快占
  name_divination.py          姓名起卦
  daily_fortune.py            当日气运
  item_search.py              寻物专项
  decision_helper.py          二选一决策
  method_selector.py          起卦法选择器 CLI
  rule_audit.py               规则数据审计 CLI

main.py                  命令行主入口
```

本项目仅作传统文化研究与象征化参考，不替代现实分析和专业意见。

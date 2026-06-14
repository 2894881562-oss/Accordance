# Accordance 应用目录

这里是项目的实际 Python 源码目录。

## 运行

```bash
python main.py
```

## 目录结构

```text
config/                    基础数据与规则
  bagua_data.py              八卦、八宫、体用生克象义
  hexagram_data.py            六十四卦全录（卦辞+爻辞+互错综映射）
  naja_data.py                京房纳甲、世应、六亲六神十二长生
  wuxing_rules.py             五行生克、天干地支、六冲六合、三合三会、刑冲合害
  daxiang_data.py             六十四卦大象传（《象传》）
  tuanzhuan_data.py           六十四卦彖传（《彖传》）      ← 新增
  shensha_data.py             神煞子系统（天乙贵人、文昌、驿马等）← 新增
  yijing_philosophy.py        人本哲学、卦德修养、吉凶处境建议
  traditional_sources.py      传统依据链、问类现实校验与实占边界

core/                    核心逻辑
  divination.py               多种起卦法（时间/动态/姓名/三爻/日卦）
  zhuanggua.py                完整装卦引擎 + 卦身 + 进神退神 + 反吟伏吟
  interpretation.py           综合解卦（纳甲+体用+用神+彖传+卦身+神煞）
  qi_context.py               气机计算（精确日干支、旬空、月建、时干支）
  question_history.py         问题历史（持久化 + 中文语义去重 + 时间梯度拦截）

modules/                 功能模块
  full_divination.py          六爻详占
  quick_divination.py         三爻快占
  name_divination.py          姓名起卦
  daily_fortune.py            当日气运
  item_search.py              寻物专项
  decision_helper.py          二选一决策

main.py                  命令行主入口
```

本项目仅作传统文化研究与象征化参考，不替代现实分析和专业意见。

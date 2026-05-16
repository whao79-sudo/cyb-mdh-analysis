# 🦞 创业板指数 MDH 假说验证

> 成交量对波动率的预测性分析 — Mixture of Distributions Hypothesis

## 📋 项目说明

本项目对 **创业板指数 (sz.399006)** 进行 MDH（混合分布）假说验证，通过三种方法检验成交量对波动率的预测能力：

1. **GARCH-X 模型** — 检验引入成交量后波动率持续性是否下降
2. **Granger 因果检验** — 成交量与波动率的因果关系方向
3. **HAR-RV 模型** — 成交量是否能提升波动率的预测精度

## 🗂️ 项目结构

```
cyb-mdh-analysis/
├── .github/workflows/
│   └── daily-analysis.yml    # GitHub Actions 定时任务
├── scripts/
│   ├── fetch_data.py         # 从 baostock 获取数据
│   └── mdh_analysis.py       # MDH 假说验证主程序
├── data/
│   └── cyb_data.db           # SQLite 数据库（数据本地存储）
├── output/
│   ├── mdh_report.md         # 分析报告（Markdown）
│   ├── mdh_report.json       # 分析报告（JSON，结构化数据）
│   └── cyb_mdh_analysis.html # 交互式图表（Plotly）
├── requirements.txt
└── README.md
```

## 🚀 使用方法

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 1. 获取数据
python scripts/fetch_data.py 2024-01-01

# 2. 运行分析
python scripts/mdh_analysis.py
```

### GitHub Actions 自动运行

- **定时**：每个交易日下午 5:30 (北京时间)
- **手动触发**：进入 Actions → "CYB MDH Daily Analysis" → "Run workflow"

## 📊 分析方法说明

### MDH 假说 (Mixture of Distributions Hypothesis)

由 Clark (1973) 提出，核心观点：
- 成交量是信息流到达速度的代理变量
- 信息流同时驱动价格波动和交易活动
- 因此成交量对波动率具有预测能力

### GARCH-X 检验

- **标准 GARCH(1,1)**: 衡量波动率聚集效应
- **GARCH-X (含成交量)**: 加入成交量作为外生变量
- **MDH 验证**: 若成交量能解释波动率，则加入后 α+β 应显著下降

### Granger 因果检验

- 检验成交量是否能 Granger 引起波动率变化
- 以及是否存在双向因果关系

### HAR-RV 模型

- 用已实现波动率的日/周/月成分预测未来波动率
- 加入成交量后比较预测精度提升

## 📈 查看结果

GitHub Pages 部署后访问：

```
https://USERNAME.github.io/cyb-mdh-analysis/output/cyb_mdh_analysis.html
```

## 📚 参考文献

- Clark, P. K. (1973). A subordinated stochastic process model with finite variance for speculative prices. *Econometrica*.
- Lamoureux, C. G., & Lastrapes, W. D. (1990). Heteroskedasticity in stock return data: Volume versus GARCH effects. *Journal of Finance*.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics*.

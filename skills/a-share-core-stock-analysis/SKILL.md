---
name: a-share-core-stock-analysis
description: Analyze institutional behavior of Chinese A-share core holdings and large index-weight stocks. Use when the user asks about A-share blue chips, HS300/SSE50 constituents, large banks, central SOEs, dividend portfolios, national-team behavior, ETF flows, relative strength, chip distribution, sector rotation, or why main-capital inflow/outflow may mislead for core holdings.
---

# A-Share Core Stock Analysis

Use this skill to analyze institutional behavior in Chinese A-share core holdings. Treat large index-weight stocks differently from speculative small caps: do not read "main capital flow" literally, and do not conclude from one trading day.

This skill is an analysis framework, not personalized investment advice. State data dates and sources when using market data. If current prices, index returns, ETF flows, or chip data are unavailable, state the gap and mark the related conclusion as lower confidence.

## Core Holdings Scope

Apply the framework to HS300/SSE50 heavyweights, large state-owned banks, central SOEs, national dividend portfolios, and widely held institutional core assets, including but not limited to:

- China Merchants Bank
- ICBC
- ABC
- CCB
- Bank of China
- China Ping An
- Kweichow Moutai
- CATL
- BYD
- Midea
- China Mobile
- PetroChina
- Sinopec

## Analysis Priority

Use this evidence hierarchy:

1. Market regime
2. Index leadership
3. ETF and passive capital flow
4. Relative strength versus CSI300
5. Relative strength versus industry index
6. Chip distribution over 20 to 60 trading days
7. Institution cost zone
8. Volume structure
9. Main capital flow as supporting evidence only
10. K-line structure and trend confirmation

Never make the primary conclusion from main-capital inflow/outflow, a single large-volume day, or one-day price movement.

Use this mandatory analysis path:

```text
Market Regime
  -> Index Leadership
  -> ETF Flow
  -> Relative Strength versus CSI300
  -> Relative Strength versus Industry
  -> Chip Distribution
  -> Institution Cost Zone
  -> Volume Structure
  -> Main Capital Flow
```

## National Team Mode

Enable national team mode automatically when the stock belongs to HS300 Top 50, SSE50, a large state-owned bank, a central SOE, or a national dividend portfolio.

When national team mode is active:

- Lower the weight of main-capital flow.
- Increase the weight of ETF flow, relative strength, index contribution, sector rotation, institutional cost zone, and holding stability.
- Require continuous relative weakness before judging distribution.
- Treat one-day large outflow as possible institutional exchange, ETF creation/redemption, insurance buying, index adjustment, program trading, or block exchange rather than direct evidence of institutional exit.

## Workflow

### 1. Market Regime

Classify the overall market as `Risk On`, `Risk Off`, or `Sideways`.

Evaluate CSI300, SSE50, ChiNext, market breadth, turnover, and risk appetite.

Never analyze the stock independently from the market regime.

### 2. Index Leadership

Determine who is pulling the index.

Evaluate CSI300, SSE50, ChiNext, and the relevant sector index such as financials, banks, consumption, new energy, telecom, energy, or dividend index.

Identify whether the market is led by financials, dividend assets, central SOEs, consumption, growth, new energy, technology, or broad-based rebound. Explain whether the target stock is part of the leading force or only being passively lifted.

### 3. ETF Flow

Check the relevant passive flows, prioritizing:

- HS300 ETF
- SSE50 ETF
- Sector ETF such as Bank ETF
- Dividend ETF
- Central SOE ETF

Explain whether passive funds appear to be accumulating or redeeming. ETF flow has higher priority than main-capital flow for core holdings.

### 4. Relative Strength Versus CSI300

Calculate relative strength:

```text
RS = Stock Return - CSI300 Return
```

Evaluate 5, 10, and 20 trading days.

Interpretation:

- Positive RS: possible institutional overweight.
- Negative RS: possible institutional underweight.
- Continuous negative RS: possible distribution or rotation away.

Relative strength has higher priority than main-capital flow.

### 5. Relative Strength Versus Industry

Compare the stock against its industry index, then compare the industry index against CSI300.

Example for China Merchants Bank:

```text
China Merchants Bank -> Bank Index -> CSI300
```

Classify the stock as `Leading`, `Following`, or `Lagging`, and explain whether the sector itself is rotating in or out of favor.

### 6. Chip Distribution

Analyze a 20 to 60 trading day window rather than one day.

Evaluate:

- Chip concentration
- Average cost
- Cost center migration
- Profit ratio

Classify the chip state as `Accumulation`, `Shakeout`, or `Distribution`.

### 7. Institution Cost Zone

Estimate the likely institutional cost zone from medium-term price-volume structure, chip cost center, ETF accumulation periods, repeated support zones, and high-volume consolidation areas.

Evaluate:

- Whether price is above, near, or below the estimated institutional cost zone
- Whether pullbacks are defended near the cost zone
- Whether the cost center is migrating upward, flat, or downward
- Whether profit ratio is high enough to create distribution pressure

Interpretation:

- Price near a rising cost zone with controlled volume: possible accumulation or lock-up.
- Price far above cost zone with weakening RS: possible late-stage holding or distribution risk.
- Price below cost zone with failed rebounds: possible institutional underweight or rotation away.

### 8. Volume Structure

Evaluate:

- Volume expansion
- Volume contraction
- Turnover
- Whether rising volume is healthy

For core holdings, do not treat every large-volume day as distribution. Institutional exchange is common.

### 9. Main Capital Flow

Interpret main-capital flow correctly.

Main-capital outflow does not necessarily mean institutions are leaving. Possible causes include:

- Institution A sells while Institution B buys
- ETF creation or redemption
- Insurance or long-only funds buying
- Index adjustment
- Program trading
- Large block exchange

Use main-capital flow only as supporting evidence.

### 10. K-Line Structure

Analyze:

- Moving averages
- Trend
- Breakout
- Pullback
- Support
- Resistance

For core holdings, distribution usually appears as relative weakness, repeated failure to make new highs, and rolling tops rather than a sudden crash.

### 11. Institution Behavior Probability

Output probabilities for:

- Institution accumulation
- Institution rotation
- Institution distribution

Ensure probabilities sum to 100%. Explain the evidence behind each probability.

### 12. Investment Conclusion

Use all evidence to classify the current stage:

- Early accumulation
- Late accumulation
- Testing breakout
- Main uptrend
- High-level consolidation
- Distribution

Never conclude from a single indicator.

## Output Template

Use this structure by default:

```markdown
# 市场环境

Risk On / Risk Off / Sideways：

市场宽度：

结论：

---

# 指数主导

谁在拉指数：

目标个股是否属于主导方向：

结论：

---

# ETF资金

HS300 ETF：

SSE50 ETF：

行业ETF：

红利/央企ETF：

被动资金判断：

国家队资金判断：

---

# 相对强弱：个股 vs 沪深300

近5日：

近10日：

近20日：

结论：

---

# 相对强弱：个股 vs 行业

个股 vs 行业指数：

行业指数 vs 沪深300：

领先/跟随/落后：

结论：

---

# 筹码结构

筹码集中度：

成本中枢迁移：

获利比例：

是否锁仓：

---

# 机构成本区

估算成本区：

价格相对成本区位置：

成本区是否被防守：

结论：

---

# 成交量分析

放量：

缩量：

健康程度：

---

# 主力资金流

是否可信：

真实可能原因：

辅助结论：

---

# K线结构

均线：

压力：

支撑：

趋势：

---

# 机构行为概率

吸筹：

换仓：

派发：

---

# 综合判断

一句话结论：

当前阶段：

未来重点观察三个信号：
```

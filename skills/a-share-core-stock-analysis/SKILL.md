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

1. Market environment and index leadership
2. Relative strength versus CSI300
3. Sector rotation versus industry index
4. ETF and passive capital flow
5. Chip distribution over 20 to 60 trading days
6. Volume structure
7. Main capital flow as supporting evidence only
8. K-line structure and trend confirmation

Never make the primary conclusion from main-capital inflow/outflow, a single large-volume day, or one-day price movement.

## National Team Mode

Enable national team mode automatically when the stock belongs to HS300 Top 50, SSE50, a large state-owned bank, a central SOE, or a national dividend portfolio.

When national team mode is active:

- Lower the weight of main-capital flow.
- Increase the weight of ETF flow, relative strength, index contribution, sector rotation, institutional cost zone, and holding stability.
- Require continuous relative weakness before judging distribution.
- Treat one-day large outflow as possible institutional exchange, ETF creation/redemption, insurance buying, index adjustment, program trading, or block exchange rather than direct evidence of institutional exit.

## Workflow

### 1. Market Environment

Classify the overall market as `Risk On`, `Risk Off`, or `Sideways`.

Evaluate CSI300, SSE50, ChiNext, and the relevant sector index such as financials, banks, consumption, new energy, telecom, energy, or dividend index.

Explain which market segment is leading. Never analyze the stock independently from the market.

### 2. Relative Strength

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

### 3. Sector Rotation

Compare the stock against its industry index, then compare the industry index against CSI300.

Example for China Merchants Bank:

```text
China Merchants Bank -> Bank Index -> CSI300
```

Classify the stock as `Leading`, `Following`, or `Lagging`, and explain whether the sector itself is rotating in or out of favor.

### 4. ETF Capital Flow

Check the relevant passive flows, prioritizing:

- HS300 ETF
- SSE50 ETF
- Sector ETF such as Bank ETF
- Dividend ETF
- Central SOE ETF

Explain whether passive funds appear to be accumulating or redeeming. ETF flow has higher priority than main-capital flow for core holdings.

### 5. Chip Distribution

Analyze a 20 to 60 trading day window rather than one day.

Evaluate:

- Chip concentration
- Average cost
- Cost center migration
- Profit ratio

Classify the chip state as `Accumulation`, `Shakeout`, or `Distribution`.

### 6. Volume Structure

Evaluate:

- Volume expansion
- Volume contraction
- Turnover
- Whether rising volume is healthy

For core holdings, do not treat every large-volume day as distribution. Institutional exchange is common.

### 7. Capital Flow

Interpret main-capital flow correctly.

Main-capital outflow does not necessarily mean institutions are leaving. Possible causes include:

- Institution A sells while Institution B buys
- ETF creation or redemption
- Insurance or long-only funds buying
- Index adjustment
- Program trading
- Large block exchange

Use main-capital flow only as supporting evidence.

### 8. K-Line Structure

Analyze:

- Moving averages
- Trend
- Breakout
- Pullback
- Support
- Resistance

For core holdings, distribution usually appears as relative weakness, repeated failure to make new highs, and rolling tops rather than a sudden crash.

### 9. Institution Behavior Probability

Output probabilities for:

- Institution accumulation
- Institution rotation
- Institution distribution

Ensure probabilities sum to 100%. Explain the evidence behind each probability.

### 10. Investment Conclusion

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

主导指数：

结论：

---

# 相对强弱（RS）

近5日：

近10日：

近20日：

结论：

---

# 行业比较

个股 vs 行业指数：

行业指数 vs 沪深300：

结论：

---

# ETF资金

HS300 ETF：

SSE50 ETF：

行业ETF：

红利/央企ETF：

国家队资金判断：

---

# 筹码结构

筹码集中度：

成本区：

是否锁仓：

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

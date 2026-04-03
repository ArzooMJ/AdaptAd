# Economic Case for Ad Agencies — AdaptAd

## The Core Argument

Ad agencies currently pay for **impressions**, not outcomes. A fatigued user who sees an ad and immediately skips it costs the same as an engaged user who watches it fully. AdaptAd changes the economics by only spending impressions where they are worth spending.

The result: fewer ads shown, but each one is worth more.

---

## Why Fewer Ads Can Mean More Revenue

### 1. Quality Impressions Command Higher CPM

The digital advertising industry already prices inventory by quality:
- Standard display: ~$2–4 CPM
- Targeted video (right audience, right time): ~$15–25 CPM
- Premium contextual placements: up to $40+ CPM

AdaptAd's decision engine only serves an ad when:
- The user's **ad tolerance is high enough** to engage
- The **content mood is not intense or dark** (brand safety)
- The **fatigue level is below the penalty threshold**
- The **ad category matches the user's interests**
- The **time of day aligns with the user's watch habits**

Every impression AdaptAd delivers meets multiple of these conditions simultaneously. That is a premium placement — it should be priced like one.

**The pitch**: agencies pay less total spend but on inventory that converts at 2–3× the rate of a standard impression. Net revenue per dollar spent goes up.

---

### 2. Suppression Is Not Waste — It Is Inventory Protection

When AdaptAd suppresses an ad, it prevents a negative association between the brand and the user's bad experience (mid-intense-scene, already seen 3 ads this session, watching at 1am while exhausted). A forced impression in that context:

- Drives skip rates up → lowers completion rate → lowers the agency's performance metrics
- Associates the brand with annoyance → measurable negative brand recall
- Pushes the user toward ad blockers → permanent impression loss

**The pitch**: every suppression is one avoided brand-damage event. The agency retains a viewer who will see their ad again next session, under better conditions.

---

### 3. The Fitness Function Already Optimises for Revenue

This is the actual system behaviour, not a claim:

```
Fitness = 60% user satisfaction + 40% advertiser revenue
```

The genetic algorithm tunes 8 parameters to maximise this combined score. Revenue is a first-class objective. The GA does not just minimise ad frequency — it finds the chromosome (policy weights) that maximises the revenue that *can* be extracted without degrading satisfaction past the point of no return.

From `fitness.py`, the revenue payouts per decision:

| Decision | Revenue score | Condition |
|---|---|---|
| SHOW | 1.00 | Relevant ad, low fatigue |
| SHOW | 0.85 | Relevant ad, high fatigue |
| SHOW | 0.65 | Irrelevant, low fatigue |
| SHOW | 0.45 | Irrelevant, high fatigue |
| SOFTEN | 0.52 | Any |
| DELAY | 0.12 | Any |
| SUPPRESS | 0.02 | Any |

The GA learns when to SHOW vs SOFTEN to maximise the sum of these values across all users and sessions. It does not blindly suppress — it finds the revenue-optimal threshold.

---

### 4. Demographic and Seasonal Precision = Less Wasted Budget

AdaptAd scores every ad opportunity against:
- **Demographic match** (age group vs. ad target demographics): +0.08 advertiser score
- **Seasonal affinity** (travel ads in summer, tech ads in winter): up to +0.12
- **Engagement level** of the user: up to +0.25

An auto ad served to a 65+ retiree with low engagement in spring is worth almost nothing to the advertiser. AdaptAd's advertiser advocate scores it low and delays or softens it. The budget is preserved for a 35-44 professional in spring with high engagement — the exact audience DriveForward or SwiftWheels is paying for.

**The pitch**: agencies stop paying to reach the wrong person at the wrong time. Targeting precision improves without any additional data collection from the user.

---

### 5. Retention Is an Economic Asset

The indirect but largest economic argument: a viewer who stays on the platform is worth more than any single ad impression.

- Average streaming subscriber LTV: $200–500/year
- A viewer driven off by ad overload: $0 from that point forward
- Churn driven by ad fatigue is well-documented in streaming research

AdaptAd's force-suppress threshold (fatigue > 0.85) is a hard ceiling that protects viewer retention. Every session that ends with the viewer still engaged is a session where the next ad opportunity exists.

**The pitch**: AdaptAd is subscriber retention infrastructure. The revenue it protects from churn exceeds the revenue it withholds in any single session.

---

## How to Frame This for the Professor

The key insight is the **trade-off reframe**:

> Traditional ad systems optimise for *volume* — show as many ads as possible.
> AdaptAd optimises for *yield* — extract the maximum sustainable revenue per viewer-hour.

These are different objective functions, and for a mature, subscription-adjacent streaming platform, yield is the better one. It aligns ad agency revenue, platform retention, and viewer satisfaction into a single optimisation target — which is exactly what the fitness function computes.

The genetic algorithm finding the right chromosome is, in economic terms, finding the **Pareto-efficient frontier** between ad revenue and viewer satisfaction.

---

## Numbers You Can Put on a Slide

These are illustrative but defensible from the data:

| Metric | Random Baseline | AdaptAd |
|---|---|---|
| Mean revenue score per break | ~0.55 (random SHOW/SUPPRESS) | 0.65–0.75 (selective SHOW) |
| % impressions on relevant users | ~30% (random) | 60–70% (filtered) |
| Mean user satisfaction score | ~0.45 | 0.60–0.70 |
| Estimated CTR improvement | 1× | 1.5–2× (relevant + low fatigue) |

Run `/simulate/session` across 50 users and average the revenue scores from the decisions — that gives you a real number from your own system to quote.

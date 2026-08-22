# Implied Volatility Surface — Skew-Adjusted Greeks on ^NDX

**Research question:** To what extent do empirical deviations from the Black–Scholes
constant-volatility assumption — manifested as an implied volatility skew in ^NDX
(Nasdaq-100 index) options — distort the theoretical valuation of option sensitivities
(Delta and Vega)?

The short version: they distort them enough to matter. On the front-month expiry
studied here, the skew-adjusted Delta differs from the flat-vol Black–Scholes Delta by
up to **0.032** (≈3.2 shares of hedge error per 100-multiplier contract), and the Vega
gap reaches **8.37 points — 333% of the flat-vol theoretical Vega at that strike**. The
error is not symmetric: it concentrates in OTM puts, consistent with the fitted
negative-ρ skew.

---

## What this repository contains

| File | Purpose |
|---|---|
| `IMP-V.ipynb` | The working analysis. Terse, code-first, minimal commentary. |
| `IMP-V-report.ipynb` | The same pipeline written up as a readable report — full derivations, modelling rationale, and interpretation of every chart. **Start here.** |
| `README.md` | This file. |

Both notebooks are committed with their outputs intact, so the charts and printed
diagnostics render on GitHub without needing to run anything.

---

## Method

The pipeline runs end-to-end from live market data, with no hardcoded rate or dividend
assumptions.

**1. Bootstrap a term-matched discount curve.**
The U.S. Treasury daily par (CMT) yield curve is fetched and bootstrapped into
continuously-compounded zero rates, then interpolated to each option's own tenor. This
replaces a flat `r = 4.5%` assumption — the zero rate, not the par yield, is the object
that belongs in `e^{-rT}` and in the BSM drift.

**2. Imply the forward and the dividend yield from the market, don't assume them.**
For each expiry, put–call parity `C − P = e^{−r_t T}(F − K)` is solved for the forward
`F` off market quotes, and the dividend yield is backed out as `q_t = r_t − ln(F/S)/T`.
A ~0.7% fallback fires only when parity is unsolvable for an expiry (no overlapping
call/put strikes surviving sanity filters).

**3. Splice the OTM wings.**
Strikes below the forward use puts; strikes at or above use calls. Under put–call
parity these should agree, so the splice yields one consistent curve built entirely from
the liquid side of the chain. ^NDX was chosen over SPY deliberately: ^NDX options are
European-style and cash-settled, so the BSM European assumption holds *exactly* — there
is no early-exercise premium to caveat.

**4. Weight quotes rather than filtering them.**
Every OTM quote passing basic sanity checks is retained. Each gets a
**Vega × liquidity** weight, `w_i = vega_i / (spread_i · OI_i)`. Vega peaks ATM and
decays in the wings, so this does double duty: it forces accuracy where the hedging P&L
actually lives, while thin wing quotes still contribute — just barely — keeping the
optimiser stable instead of starving on a quiet session.

**5. Fit SSVI, not per-slice SVI.**
A single shared power-law SSVI surface (Gatheral & Jacquier, 2013) with parameters
`(ρ, η, γ)` is calibrated *jointly* across expiries, with a monotone-enforced ATM total
variance term structure `θ(t)`. Fitting raw SVI slice-by-slice has nothing structurally
preventing total variance from decreasing between adjacent tenors — a calendar-spread
arbitrage. The joint SSVI fit satisfies a sufficient condition for the entire continuous
surface to be calendar-arbitrage-free, and this is then verified empirically on the
fitted grid.

**6. Make the smile dynamics explicit.**
Pricing each strike off its own fitted IV gives a *sticky-strike* Delta — it says
nothing about how that strike's IV moves when spot moves. Since index skews sit much
closer to sticky-moneyness, the report applies that backbone:

$$\Delta_{\text{skewed}} = \Delta_{BS}(\sigma_{SSVI}(K)) + \text{Vega}_{BS}(\sigma_{SSVI}(K)) \cdot \frac{\partial\sigma}{\partial S}, \qquad \Psi = \Delta_{\text{skewed}} - \Delta_{BS,\text{flat}}$$

with `∂σ/∂S` obtained by central-differencing the fitted surface under a bumped spot.
This is a stated modelling choice, not a model-free fact, and it drives the sign and
size of every Delta result below.

---

## Headline results

Snapshot: ^NDX at **28,200.74**, front month **2026-08-24** (T = 0.082y), 18 OTM quotes.

**Fitted front-month SSVI:** ρ = −0.487, η = 1.077, γ = 0.441 — negative ρ, i.e. skew
tilted toward OTM puts, as expected for index options.

| Metric | Value |
|---|---|
| Max Delta distortion, sticky-strike only | 0.0722 (K = 25,600) |
| Max Delta distortion Ψ, sticky-moneyness | 0.0321 (K = 24,500) |
| Mean \|Ψ\| across fitted range | 0.0159 |
| Max Vega gap | 8.369 (K = 24,500) — 333% of theoretical |
| Mean \|Vega gap\| | 3.422 |
| Mean relative Vega gap | 53.8% |
| Calendar-arbitrage-free (Gatheral–Jacquier) | True |
| Min total-variance step between adjacent expiries | +2.37e-03 (≥ 0 ✓) |

**Asymmetry.** Mean \|Ψ\| is 0.0168 for OTM puts vs 0.0144 for OTM calls. The Vega split
is far starker: mean gap 5.35 below spot vs 0.39 above — a 14× concentration in the put
wing.

**Answer.** Constant-volatility Black–Scholes systematically mis-states hedge sensitivity
away from the ATM strike, with error growing toward the wings and split asymmetrically
between puts and calls. The magnitude is large enough to matter for a delta-hedged book,
not a rounding artifact of the fitting procedure.

---

## Known limitations

Stated plainly, because they bound what the results support:

- **One trading day.** Everything is a single cross-section. It establishes the
  constant-vol assumption is wrong *on this day* in a specific, reproducible way. It does
  *not* establish that the distortion is stable across time. Confirming "systematic" in
  the time-series sense requires re-running the pipeline over a rolling window (20–60
  sessions) and checking the sign and rough magnitude of Ψ persist.
- **Negative implied dividend yields.** Several expiries back out `q_t` between −1.4%
  and −24.7%. A negative implied dividend on an index is not economically meaningful; it
  is a symptom of the parity solve running on non-synchronous or stale
  last-trade/mid quotes from the free data feed, and is most severe at the shortest tenor
  (−24.7% at T = 0.016y, where a small forward error is divided by a tiny T). It
  propagates into the forward and therefore into the moneyness axis. Live, timestamped
  bid/ask snapshots would largely resolve this.
- **SSVI fits the single slice worse than the polynomial** (0.0283 vs 0.0120 residual
  std error on the front month). This is expected and is the intended trade: SSVI gives
  up per-slice fit quality in exchange for a globally arbitrage-free surface. The
  polynomial is a fit; SSVI is a model.
- **Sticky-moneyness is an assumption.** The empirical literature supports it for index
  skew, but the Ψ figures are conditional on it. Under pure sticky-strike, Ψ collapses to
  the sticky-strike numbers.
- **Thin front-month chain.** 18 OTM quotes, and one of five expiries needed the
  fallback dividend. Wing estimates are correspondingly noisy.

---

## Running it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install numpy pandas matplotlib scipy yfinance
jupyter lab IMP-V-report.ipynb
```

Then run all cells. The notebook fetches live data on execution, so your numbers will
differ from the committed outputs — the committed run is the snapshot documented above.

Requires network access to Yahoo Finance (option chains) and
`home.treasury.gov` (par yield curve).

---

## References

- Gatheral, J. & Jacquier, A. (2013). *Arbitrage-free SVI volatility surfaces.*
  Quantitative Finance, 14(1), 59–71.
- Derman, E. (1999). *Regimes of Volatility.* Goldman Sachs Quantitative Strategies
  Research Notes.
- Bergomi, L. (2016). *Stochastic Volatility Modeling*, ch. 2. CRC Press.
- Gatheral, J. (2006). *The Volatility Surface: A Practitioner's Guide.* Wiley.

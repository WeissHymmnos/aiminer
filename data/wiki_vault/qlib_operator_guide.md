---
title: "Qlib Operator & Formula Reference"
slug: "qlib_operator_guide"
type: "technical_ref"
status: "baseline"
summary: "Qlib Operator & Formula Reference"
updated: "2026-04-13T03:59:35.160210"
tags: []
related: []
---

# Qlib Operator & Formula Reference  
*Internal Wiki – concise cheat-sheet for modelers & pipeline builders*  

---

## 1. Purpose & Scope  
- Central lookup for every in-fix, prefix and function-style operator that can legally appear inside a `Qlib` feature expression (`<field>`, `<operator>`, `<constant>`).  
- Guarantees reproducible alpha when the same expression is evaluated on **any** compatible data source (local `.bin`, Arctic, Mongo, ClickHouse).  
- Covers:  
  - Element-wise numeric / logical / string operators  
  - Cross-sectional (group) operators  
  - Time-series (rolling / expanding) operators  
  - Specialised operators (rank, neutralise, tail-cut, etc.)  
- **Out-of-scope**: data loader DSL, model definition YAML, back-test config.  

---

## 2. Expression Grammar (EBNF)  
```ebnf
expr      :=  field
            | constant
            | "(" expr ")"
            | expr infix_op expr
            | prefix_op expr
            | func_name "(" [expr {"," expr}] ")"
field     :=  "$" identifier          -- e.g. $close, $volume
constant  :=  number | bool | string
infix_op  :=  "+" | "-" | "*" | "/" | "**" | "%" | ">" | ">=" | "<" | "<=" | "==" | "!=" | "&" | "|" | "?"
prefix_op :=  "-" | "~" | "!"
func_name :=  <see tables below>
```

---

## 3. Operator Taxonomy  

| Family | Typical Syntax | Output Type | NaN Propagation | Comment |
|---|---|---|---|---|
| **A. Arithmetic** | `+ - * / ** %` | float | yes | IEEE-754; `0/0 → NaN` |
| **B. Logical** | `> >= < <= == !=` | bool | yes | Any NaN operand ⇒ NaN (three-value logic) |
| **C. Boolean** | `& \| ~` | bool | yes | Bit-wise on bools; `&` and `\|` are **not** short-circuit |
| **D. Conditional** | `x ? y : z` | promoted | yes | Qlib ternary; both branches evaluated (vectorised) |
| **E. Cross-sectional** | `Rank(x)`, `GroupNeutral(x, group)` | float / bool | per section | See §4.3 |
| **F. Time-series** | `Ref(x,d)`, `Mean(x,n)`, `Cov(x,y,n)` | float | rolling window | See §4.4 |
| **G. Special** | `Cut(x, min, max)`, `IsValid(x)` | float / bool | defined per func | See §4.5 |

---

## 4. Operator Catalogue  

### 4.1 Arithmetic & Logical (element-wise)  
| Op | Alias | Formula | NaN rule | Caution |
|---|---|---|---|---|
| `**` | Pow | a**b | NaN if a<0 & b non-integer | Int exponent faster (`PowI(x,3)`) |
| `%` | Mod | a%b | NaN if b=0 | Use `SafeMod(a,b,alt=0)` to suppress |

### 4.2 Boolean & Conditional  
| Op | Truth table note |
|---|---|
| `==` | `NaN==NaN → NaN` (SQL-style). Use `IsEqual(x,y)` for `NaN` equality. |
| `x?y:z` | Both y & z evaluated; ensure no side-ops inside. |

### 4.3 Cross-sectional (snapshot)  
| Name | Signature | Returns | Standard pattern | Caution |
|---|---|---|---|---|
| `Rank` | `Rank(x, ascending=True, pct=False)` | float | `Rank($pe)` | Tied values get **average** rank. |
| `GroupMean` | `GroupMean(x, group, skipna=True)` | float | `GroupMean($roe, $industry)` | `group` must be categorical field. |
| `GroupNeutral` | `GroupNeutral(x, group)` | float | `$close / GroupMean($close, $industry)` | Result **mean-zero** within group. |
| `Scale` | `Scale(x, scale=1)` | float | `Scale($alpha)` | Σ\|x\| = scale across section. |
| `Cut` | `Cut(x, min=-3, max=3, fill=0)` | float | `Cut($zscore)` | Hard clip; no winsorise. |

### 4.4 Time-series (rolling window)  
| Name | Signature | NaN handling | Std pattern | Notes |
|---|---|---|---|---|
| `Ref` | `Ref(x, d)` | copy | `Ref($close,-5)` | d<0 ⇒ future (leak guard). |
| `Mean` | `Mean(x, n)` | skipna | `Mean($close,20)` | EWMA via `EWM(x,span)` |
| `Std` | `Std(x, n, ddof=0)` | skipna | `Std($ret,60)` | Population std (ddof=0). |
| `Cov` | `Cov(x,y, n)` | pairwise skip | `Cov($ret, $bm, 252)` | |
| `Corr` | `Corr(x,y, n)` | pairwise skip | `Corr($high, $low, 20)` | Pearson only. |
| `Max` / `Min` | `Max(x, n)` | skipna | `Max($high,10)` | |
| `ArgMax` | `ArgMax(x, n)` | returns offset | `ArgMax($close,20)` | 0-based look-back index. |
| `Sum` | `Sum(x, n)` | skipna | `Sum($volume,5)` | |
| `Prod` | `Prod(x, n)` | skipna | `Prod(1+$ret,21)-1` | cumulative return. |
| `Decay` | `Decay(x, f)` | EW | `Decay($signal,0.9)` | `out_t = f*out_{t-1} + (1-f)*x_t` |
| `TSRank` | `TSRank(x, n)` | skipna | `TSRank($pe, 63)` | time-series rank (0-1). |

**Rolling window boundary rules**  
- Left-aligned, closed on right.  
- Minimum valid observations = **1** (change via `min_periods=k` in YAML).  
- Future leak guard: positive `d` in `Ref` raises `ExpressionError` at parse time.  

### 4.5 Special utility  
| Name | Signature | Purpose |
|---|---|---|
| `IsValid` | `IsValid(x)` | False for NaN/inf. |
| `Log` | `Log(x, base=e)` | Natural log; `x≤0 → NaN`. |
| `Sign` | `Sign(x)` | {-1,0,1}. |
| `Abs` | `Abs(x)` | |
| `PowI` | `PowI(x, int p)` | Fast integer power. |
| `If` | `If(cond, x, y)` | Alias for ternary `cond?x:y`. |
| `CutWin` | `CutWin(x, q=0.05)` | Winsorise at quantile. |
| `DropNA` | `DropNA(x)` | Forward-fill then drop remaining NaN (pipeline pre-op). |

---

## 5. Type Promotion Matrix  

| LHS \ RHS | bool | int | float | Comment |
|---|---|---|---|---|
| bool | bool | int | float | |
| int | int | int | float | |
| float | float | float | float | |
| string | – | – | – | Only `==` / `!=` allowed; no arithmetic. |

---

## 6. NaN & Inf Policy  
- **Propagate by default**: any NaN operand → NaN result (except specialised funcs).  
- **Cross-sectional ops** skip NaN **per instrument**; window size unchanged.  
- **Inf** is treated as ordinary value except:  
  - `Corr/Cov` → NaN if any Inf in window.  
  - `Log` → NaN.  

---

## 7. Performance Cheat-Sheet  
- Prefer built-in vectorised ops; avoid nested Python lambdas.  
- Use `PowI(x,2)` vs `x**2` → 2× speed-up.  
- Replace `Rank(..., pct=True)` with `Rank(...)/Count()` when reused.  
- Rolling ops on **aligned** multiple fields share one window index → cache friendly.  

---

## 8. Common Pitfalls (Cautionary Notes)  
1. **Look-ahead**: positive `Ref` offset passes parser but raises at **run-time** if data loader feeds future data.  
2. **Tied ranks**: `Rank` averages ties; for competition scoring use `Rank(..., pct=True)`.  
3. **Window size vs calendar**: `n` is **bar count**, not calendar days; adjust for holidays.  
4. **Group field consistency**: `GroupNeutral` with stale `group` mapping leaks forward information.  
5. **String comparison**: only `==` / `!=` supported; case-sensitive.  
6. **Chained ternary**: `a?b:c?d:e` is **right-associative**; use parentheses for clarity.  
7. **Division by zero**: produces NaN; use `SafeDiv(x,y,alt=0)` wrapper for stable alpha.  

---

## 9. Migration Quick-Map (Excel → Qlib)  

| Excel | Qlib equivalent | Note |
|---|---|---|
| `AVERAGE(B2:B11)` | `Mean($field,10)` | |
| `RANK(B2,B$2:B$11,1)` | `Rank($field, ascending=True)` | |
| `STDEV(B2:B11)` | `Std($field,10, ddof=1)` | Qlib default `ddof=0`. |
| `CORREL(B2:B11,C2:C11)` | `Corr($field1,$field2,10)` | |
| `IFERROR(x,y)` | `IsValid(x)?x:y` | |

---

## 10. Mini-Recipe Gallery  

**Momentum**  
```qlib
$close / Ref($close, 20) - 1
```

**Volatility-adjusted momentum**  
```qlib
($close / Ref($close, 20) - 1) / Std($close/Ref($close,1)-1, 20)
```

**Industry-neutral ROE**  
```qlib
GroupNeutral($roe, $industry)
```

**Cross-sectional z-score**  
```qlib
($field - Mean($field, section='all')) / Std($field, section='all')
```

**Tail-cut signal**  
```qlib
Cut(Rank($signal), min=0.1, max=0.9)
```

---

## 11. References & Source  
- `qlib.data.ops` – Cython implementation (`_ops.pyx`).  
- Unit tests: `tests/test_ops.py` – authoritative behaviour.  
- Design doc: `docs/developer/operator_design.md` (internal repo).
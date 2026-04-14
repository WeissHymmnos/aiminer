import polars_plugins

expr = "If(Greater(Rank(Std(Delta($close, 1) / Ref($close, 1), 20)), 0.75), 1, 0) * Rank(Corr(($high - If(Greater($open, $close), $open, $close)) / ($high - $low), $volume / Median($volume, 20), 3))"

res = polars_plugins.compile_alpha(expr)
print(res)

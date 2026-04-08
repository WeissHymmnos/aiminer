import polars as pl
df = pl.DataFrame({
    'datetime': ['d1', 'd2', 'd3', 'd4', 'd1', 'd2', 'd3', 'd4'],
    'instrument': ['A', 'A', 'A', 'A', 'B', 'B', 'B', 'B'],
    'close': [10.0, 11.0, 12.0, 13.0, 20.0, 19.0, 18.0, 17.0]
})
# Let's try chained over
expr = pl.col('close').rolling_mean(2).over('instrument').rank().over('datetime')
print(df.with_columns(expr))

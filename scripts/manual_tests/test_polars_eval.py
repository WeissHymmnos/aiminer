import polars as pl

df = pl.DataFrame(
    {
        "datetime": [
            "2020-01-01",
            "2020-01-01",
            "2020-01-02",
            "2020-01-02",
            "2020-01-03",
            "2020-01-03",
        ],
        "instrument": ["A", "B", "A", "B", "A", "B"],
        "close": [10, 20, 11, 19, 12, 18],
        "volume": [100, 200, 150, 150, 200, 100],
    }
).sort(["instrument", "datetime"])


def Mean(e, n):
    return e.rolling_mean(
        window_size=n
    )  # Need to apply over instrument later or assume dataframe is sorted and grouped


# Wait, rolling over in polars is better with group_by
# Better yet, df.select( pl.col('close').rolling_mean(2).over('instrument') )


def Rank(e):
    return e.rank() / e.count()  # over datetime?


# Wait, over() cannot be nested easily if they clash?
# Let's test if we can do nested over():
# e.g., Rank(Mean(close, 2)) -> pl.col('close').rolling_mean(2).over('instrument').rank().over('datetime')

expr = pl.col("close").rolling_mean(2).over("instrument").rank().over("datetime")
res = df.with_columns(factor=expr)
print(res)

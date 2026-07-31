import pytest
import pandas as pd
from data_analysis import calculate_moving_average

def test_ma():
    df = pd.DataFrame({"close": [1,2,3,4,5]})
    df.index = pd.date_range("2020-01-01", periods=5)
    res = calculate_moving_average(df, period=3)
    assert "ma_3" in res.columns
    assert res["ma_3"].iloc[-1] == pytest.approx((3+4+5)/3)
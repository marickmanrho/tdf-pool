import pandas.testing as pt
import numpy as np

from tdf_pool.race_calendar import get_races


def test_2024_1_UWT_calendar():
    expected = [
        "Cadel Evans Great Ocean Road Race",
        "Omloop Het Nieuwsblad ME",
        "Strade Bianche",
        "Milano-Sanremo",
    ]

    results = get_races(2024).loc[:4, "Race"].values

    assert np.allclose(expected, results)

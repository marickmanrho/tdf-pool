import logging

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, milp

_logger = logging.getLogger(__name__)


def select_best_team(riders: pd.DataFrame, nriders: int = 15, budget: int = 100):
    _logger.info(
        "Finding best team of %s riders within a total budget of %s from a group of %s riders",
        nriders,
        budget,
        len(riders),
    )

    # milp function only minimizes, so we create negative objective function
    objective_function = -1 * riders["Points"].values

    # The sum of all selected riders must be exactly nriders
    nriders_constraint = LinearConstraint(
        np.ones_like(objective_function), nriders, nriders
    )

    # The total price of riders may not exceed the budget
    budget_constraint = LinearConstraint(riders["Price"], 0, budget)

    # Use mixed-integer linear programming (milp) to find result
    # integrality = 1 means only integer values are allowed
    optimized_result = milp(
        objective_function,
        integrality=np.ones_like(objective_function),
        bounds=(0, 1),
        constraints=[nriders_constraint, budget_constraint],
    )
    _logger.debug(optimized_result.message)
    return optimized_result.x, optimized_result.fun


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    race_scores = pd.read_csv("scores_2023.csv")
    rider_price = pd.read_csv("prices.csv", sep=";")

    print(race_scores.head())

    riders = race_scores.assign(Price=rider_price["Price"])
    selection, selection_points = select_best_team(riders, nriders=15)

    print(f"points of best team = {selection_points}")
    print(riders.loc[selection == 1])

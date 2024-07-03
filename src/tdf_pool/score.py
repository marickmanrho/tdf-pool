import logging
import os
import tomllib
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from tdf_pool.race import Race
from tdf_pool.stage import Stage

_logger = logging.getLogger(__name__)


def get_score_template(filepath: Path | None = None) -> dict:
    if filepath is None:
        filepath = Path(os.getenv("SCORE_TEMPLATE"))
    with open(filepath, "rb") as file:
        score_template = tomllib.load(file)
    return score_template


def score_stage(stage: Stage, score_template: dict) -> pd.DataFrame | None:
    podia = []
    # Apply all stage scoring templates
    _logger.info("Scoring %s", stage)
    for kwargs in score_template["stage"].values():
        if stage.stage_name is None:
            continue
        podium = scoring_function(stage, **kwargs)
        if podium is not None:
            podia.append(podium)

    if len(podia) == 0:
        return None

    podium = pd.concat(podia).groupby(["Rider", "Team"]).agg("sum").reset_index()

    # compute total points
    point_columns = [col for col in podium.columns if col not in ["Rider", "Team"]]
    podium["Total"] = podium[point_columns].sum(axis=1)
    podium = podium.sort_values(by="Total", ascending=False)
    return podium


def score_race(
    race: Race, score_template: dict, score_stages: bool = True
) -> pd.DataFrame:
    podia = []
    # Score all individual stage
    if score_stages:
        for stage in race.stages:
            _logger.debug("Scoring  %s", stage)
            podium = score_stage(stage, score_template)
            if podium is not None:
                podia.append(podium)

    # Score the total race
    _logger.info("Scoring %s", race)
    if len(race.stages) > 0:
        for kwargs in score_template["race"].values():
            podium = scoring_function(race.stages[-1], **kwargs)
            if podium is not None:
                podia.append(podium)

    if len(podia) == 0:
        return None
    podium = pd.concat(podia).groupby(["Rider", "Team"]).agg("sum").reset_index()

    # compute total points
    point_columns = [
        col for col in podium.columns if col not in ["Rider", "Team", "Total"]
    ]
    podium["Total"] = podium[point_columns].sum(axis=1)
    podium = podium.sort_values(by="Total", ascending=False)
    return podium


def scoring_function(
    stage: Stage,
    key: str | list[str],
    key_filter: str | list[str] | None = None,
    rank_by: str = "Rnk",
    points: list[int] | None = None,
    name: str | None = None,
    ascending: bool = True,
    strict: bool = False,
) -> pd.DataFrame:
    # Make sure key is a list
    key = key if isinstance(key, list) else [key]
    key_filter = key_filter or []
    key_filter = [key_filter] if isinstance(key_filter, str) else key_filter

    # Set default name if not given
    name = name or rank_by

    # Return columns
    return_columns = ["Rider", "Team", name]

    # Extract result table
    results = stage.results
    for k in key:
        if k in results:
            results = results[k]
        elif strict:
            raise ValueError(f"key {k} not in stage results")
        else:
            _logger.debug("Key %s not found in results, returning empty dataframe", k)
            return None

    # If not a dataframe, raise error
    if isinstance(results, pd.DataFrame):
        results = {"general": results}
    elif not isinstance(results, dict):
        if strict:
            raise TypeError(
                f"Results is not a DataFrame or a dict containing DataFrames but a {type(results)}"
            )
        return None

    podia = []
    for result_name, result in results.items():
        if result_name in key_filter:
            _logger.debug(
                "Subtable %s is in key filter, appending empty dataframe.", result_name
            )
            podia.append(None)
            continue
        _logger.debug("Parsing %s subtable", result_name)

        # Filter riders that didn't finish
        if "Rnk" in result.columns:
            result = result[
                ~result["Rnk"].isin(["DNF", "DNS", "NR", "DSQ", "OTL", "DF"])
            ]

        # If there is no result, don't score riders
        if len(result) == 0:
            if strict:
                raise ValueError("Empty dataframe supplied")
            _logger.debug("Dataframe is empty, score no points")
            podia.append(None)
            continue

        # Make sure required columns are available
        required_columns = ["Rider", "Team", rank_by]
        if isinstance(points, str):
            _logger.debug(
                "`points` is a string, hence the points are extracted from the %s column",
                points,
            )
            required_columns.append(points)

        try:
            result = result[required_columns]
        except KeyError as e:
            if strict:
                raise e
            _logger.debug("Required columns %s not in dataframe", required_columns)
            podia.append(None)
            continue

        result = result.astype({rank_by: int})
        result = result.sort_values(by=rank_by, ascending=ascending).reset_index()
        if isinstance(points, str):
            result[name] = result[points].astype(int)
        else:
            # Trim points to match length of result
            if len(result) < len(points):
                _logger.debug(
                    "Result list is smaller than point list (%s < %s). Truncating point list",
                    len(result),
                    len(points),
                )
                points = points[(-1 * len(result)) :]
            riders_with_points = len(points)
            _logger.debug("Scoring %s riders with points", riders_with_points)
            result = result.iloc[range(riders_with_points)]

            result[name] = points

        result = result[return_columns]
        _logger.debug(
            "Result has length %s and columns %s", len(result), result.columns
        )
        podia.append(result)

    podia = [podium for podium in podia if podium is not None]
    if len(podia) == 0:
        return None

    podium = (
        pd.concat(podia)
        .groupby(["Rider", "Team"])
        .agg("sum")
        .reset_index()
        .sort_values(name, ascending=False)
        .astype({"Rider": str, "Team": str, name: int})
    )
    return podium


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level="DEBUG")
    default_score_template = get_score_template()
    # tdf = Race(
    #     "Tour de France", date(2023, 7, 1), "2.UWT", "race/tour-de-france/2023/gc"
    # )
    # final_score = score_race(tdf, default_score_template)
    # print(final_score.sort_values(by="Total", ascending=False).reset_index().head(50))

    stage = Stage(
        "Tour de Suisse",
        "Chur - Oberwil-Lieli",
        date(2023, 6, 16),
        6,
        "race/tour-de-suisse/2023/stage-6",
        "Stage",
    )
    final_score = score_stage(stage, default_score_template)
    print(final_score)

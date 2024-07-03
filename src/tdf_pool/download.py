import logging
import os
from pathlib import Path
from random import random
from time import sleep

import requests

_logger = logging.getLogger(__name__)


def download_webpage(
    url: str,
    filepath: Path,
    strict: bool = True,
    overwrite: bool = False,
    cooldown: float | int | None = None,
) -> None:

    if not filepath.parent.exists():
        if strict:
            raise FileNotFoundError(
                f"Folder {filepath.parent.name} doesn't exist. Turn off strict mode to create the folder."
            )
        _logger.info("Creating folder %s", filepath.parent.name)
        filepath.parent.mkdir(parents=True, exist_ok=True)

    if filepath.exists():
        if strict:
            raise FileExistsError(
                f"File {filepath.name} already exists. Turn of strict mode to overwrite the existing file."
            )
        elif not overwrite:
            _logger.debug("[   ] file %s already exists, skipping.", filepath.name)
            return
        _logger.info("[   ] file %s already exists, overwriting.", filepath.name)

    page = requests.get(url, timeout=5)

    with open(filepath, "wb") as file:
        file.write(page.content)

    _logger.info("[ OK ] downloaded %s into %s", url, filepath)

    cooldown = cooldown or 2 + 4 * random()
    _logger.debug("[    ] initiating cooldown of %s seconds", cooldown)
    sleep(cooldown)


def construct_race_name(race: str):
    """Returns the internal name of a race."""
    race_unhyphened_name = race.replace("-", " ")
    race_hyphened_name = "-".join(
        [s.strip() for s in race_unhyphened_name.split(" ") if s != ""]
    )
    return race_hyphened_name


def get_race_folderpath(race: str, year: int) -> Path:
    race_name = construct_race_name(race)
    data_folder = Path(os.getenv("DATA_FOLDER"))
    return data_folder / str(year) / race_name


def get_stage_filepath(race: str, year: int, stage: int = 1) -> Path:
    race_name = construct_race_name(race)
    stage_filename = f"{race_name}_{year}_stage-{stage}.html"
    race_folder = get_race_folderpath(race, year)
    return race_folder / stage_filename


def get_overview_filepath(race: str, year: int) -> Path:
    race_name = construct_race_name(race)
    race_path = get_race_folderpath(race, year)
    return race_path / f"{race_name}_{year}_overview.html"


def get_startlist_filepath(race: str, year: int) -> Path:
    race_name = construct_race_name(race)
    race_path = get_race_folderpath(race, year)
    return race_path / f"{race_name}_{year}_startlist.html"


def get_calender_filepath(year: int) -> Path:
    data_folder = Path(os.getenv("DATA_FOLDER"))
    return data_folder / str(year) / f"calendar_{year}.html"


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    download_webpage(
        f"https://www.procyclingstats.com/races.php?year=2024",
        filepath=get_calender_filepath(2024),
    )

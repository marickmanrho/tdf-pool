from typing import Literal, get_args

# import pandas as pd
from itertools import product
from pathlib import Path
from datetime import date

from tdf_pool.download import download_webpage

# The classification codes used by the ICU
# The general codes can be one or multi-day races
GeneralClass = Literal["UWT", "WWT", "Pro", "1", "2", "NCup", "2U"]
GENERAL_CLASS: list[GeneralClass] = list(get_args(GeneralClass))
# The special codes are by definition one-day races
SpecialCLass = Literal[
    "WC",
    "NC",
    "Olympics",
]
SPECIAL_CLASS: list[SpecialCLass] = list(get_args(SpecialCLass))

# A duration mapping from function input to UCI code
Duration = Literal["one-day", "multi-day"]
DURATION_ABBREVIATIONS = {"one-day": "1", "multi-day": "2"}

# The categories used by procyclingstats.com and their abbreviations
Category = Literal["Elite", "U23", "Juniors"]
CATEGORY_ABBREVIATIONS: dict[Category, str] = {c: c[0] for c in get_args(Category)}

# The genus used and their abbreviations
Genus = Literal["Men", "Women"]
GENUS_ABBREVATIONS: dict[Genus, str] = {g: g[0] for g in get_args(Genus)}

# Mapping used by procyclingstats.com to filter race results
CLASS_MAP = {
    "ME": 1,
    "WE": 2,
    "MU": 3,
    "MJ": 4,
    "WJ": 6,
    "WU": 7,
}


def ensure_list_or_default[T](value: T | list[T], default: list[T]) -> list[T]:
    """Set default value and ensure list type

    If the input value is a list, it is simply returned.
    If it is None, the default value is returned.
    When the value is something else, it is made into a list.

    Args:
        value T | list[T]: Value to be set to default if none and ensured to be a list.
        defaults list[T]: Default values to use when value is None.

    Raises:
        TypeError: When default is not a list.

    Returns:
        list: A list of value or the default.
    """
    if not isinstance(default, list):
        raise TypeError("default must be a list.")

    match value:
        case None | []:
            return default
        case [_]:
            return value
        case _:
            return [value]


def get_race_url(year, classification, category, duration, genus) -> str:
    # Construct URL
    cat_string = GENUS_ABBREVATIONS[genus] + CATEGORY_ABBREVIATIONS[category]
    cat_number = CLASS_MAP[cat_string]
    if classification in SPECIAL_CLASS:
        if duration == "multi-day":
            # Special classifications (like olympics and world cups) are only one-day.
            return None
        full_classification = classification
    else:
        # Create the full classification code like 1.UWT or 2.Pro
        full_classification = ".".join(
            [DURATION_ABBREVIATIONS[duration], classification]
        )

    url = (
        f"https://www.procyclingstats.com/races.php"
        f"?season={year}"
        f"&category={cat_number}"
        f"&racelevel=&pracelevel=smallerorequal&racenation="
        f"&class={full_classification}"
        f"&filter=Filter&p=uci&s=calendar-plus-filters"
    )
    return url


def get_calendar_filename(
    year: str | int,
    classification: GeneralClass | SpecialCLass,
    category: Category,
    duration: Duration,
    genus: Genus,
) -> Path:
    return Path(f"calendar_{year}_{classification}_{category}_{duration}_{genus}.html")


def get_races(
    year: int | list[int],
    classification: (
        GeneralClass | SpecialCLass | list[GeneralClass | SpecialCLass] | None
    ) = None,
    category: Category | list[Category] | None = None,
    duration: Duration | None = None,
    genus: Genus | list[Genus] | None = None,
):  # -> pd.DataFrame:
    """Returns a list of all races

    Args:
        year (int | list[int]): Year or list of years.
        classification (GeneralClass  |  SpecialCLass  |  list[GeneralClass  |  SpecialCLass]  |  None, optional): UCI classification code or list of codes without duration indication. Defaults to None.
        category (Category | list[Category] | None, optional): Procyclingstats category or list of categories. Defaults to None.
        duration (Duration | None, optional): Duration of race, one-day or multi-day. Defaults to None.
        genus (Genus | list[Genus] | None, optional): Genus filter like Men or Women. Defaults to None.

    Returns:
        pd.DataFrame: List of races that match the input filters.
    """

    # Set defaults and ensure list types
    year = ensure_list_or_default(year, [date.today().year])
    classification = ensure_list_or_default(
        classification, GENERAL_CLASS + SPECIAL_CLASS
    )
    category = ensure_list_or_default(category, list(CATEGORY_ABBREVIATIONS.keys()))
    duration = ensure_list_or_default(duration, list(DURATION_ABBREVIATIONS.keys()))
    genus = ensure_list_or_default(genus, list(GENUS_ABBREVATIONS.keys()))

    # For each combination of filters, get the webpage and extract the calendar table
    for y, c, cat, d, g in product(year, classification, category, duration, genus):
        url = get_race_url(y, c, cat, d, g)
        calendar_filename = get_calendar_filename(y, c, cat, d, g)
        print(url)
        download_webpage(url, calendar_filename)
    # Combine all calendar tables


if __name__ == "__main__":
    get_races(2024, classification="WWT", category="Elite", genus="Women")

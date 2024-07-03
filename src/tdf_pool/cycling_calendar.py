import logging
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from lxml import etree

from tdf_pool.download import download_webpage, get_calender_filepath
from tdf_pool.race import Race

_logger = logging.getLogger(__name__)


def get_calendar(year: int = 2024) -> pd.DataFrame:
    calendar_filepath = get_calender_filepath(year)
    # Download calendar
    download_webpage(
        f"https://www.procyclingstats.com/races.php?year={year}",
        filepath=calendar_filepath,
        strict=False,
    )

    # Load races file``
    with open(calendar_filepath, "r", encoding="utf-8") as file:
        tree = etree.HTML(str(file.read()))

    races = tree.xpath("//table/tbody/tr")
    race_data = []
    for race in races:
        columns = list(race.xpath("td"))

        # Get the dates and convert to date object
        dates = columns[0].text.split(" - ")
        start_day, start_month = dates[0].split(".")
        start_date = date(year, int(start_month), int(start_day))
        if len(dates) > 1:
            end_day, end_month = dates[1].split(".")
            end_date = date(year, int(end_month), int(end_day))
        else:
            end_date = start_date

        # Get rid of newlines and whitespace in race name
        race_name = "".join(
            [s.strip() for s in columns[2].xpath("a")[0].text.split("\n")]
        )

        # Get race partial url and race type
        race_url = columns[2].xpath("a")[0].attrib["href"]
        race_type = columns[4].text

        # Write a record
        race_data.append([start_date, end_date, race_name, race_url, race_type])

    races = pd.DataFrame(
        race_data, columns=["Start", "End", "Name", "PartialURL", "Type"]
    )
    _logger.info("[ OK ] Read race calender of %s", year)
    return races


def get_races_between(date_start: date, date_end: date) -> list[Race]:
    year_start = date_start.year
    year_end = date_end.year

    calenders = [get_calendar(year) for year in range(year_start, year_end + 1)]
    complete_calendar = pd.concat(calenders)
    filtered_calendar = complete_calendar[
        complete_calendar["Start"].between(date_start, date_end)
    ]
    races = [
        Race(race["Name"], race["Start"], race["Type"], race["PartialURL"])
        for _, race in filtered_calendar.iterrows()
    ]
    return races


# def download_all_races_from_calendar(year: int = 2024, max_date: date | None = None):
#     max_date = max_date or date.today()
#     calendar = get_calendar(year)

#     for _, race in calendar.iterrows():
#         if race["Start"] > max_date:
#             continue
#         if race["Type"] == "1.UWT":
#             # One day race, directly download result list
#             download_webpage(
#                 "https://www.procyclingstats.com/" + race["PartialURL"],
#                 filepath=get_stage_filepath(race["Name"], year),
#                 strict=False,
#             )
#         if race["Type"] == "2.UWT":
#             # Multi day race, download individual stages

#             # Get overview page instead of final gc
#             overview_page_link = "https://www.procyclingstats.com/" + race[
#                 "PartialURL"
#             ].replace("/gc", "")
#             download_webpage(
#                 overview_page_link,
#                 filepath=get_overview_filepath(race["Name"], year),
#                 strict=False,
#             )

#             # Get list of stages
#             stages = list_multiday_race_stages(race["Name"], year)

#             # download all stages
#             for idx, stage in stages.iterrows():
#                 download_webpage(
#                     "https://www.procyclingstats.com/" + stage["PartialURL"],
#                     filepath=get_stage_filepath(race["Name"], year, stage=idx + 1),
#                     strict=False,
#                 )


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level="INFO")
    calendar = get_calendar(2024)
    print(calendar.head())

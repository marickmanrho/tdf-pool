import logging
from datetime import date
import pandas as pd
from dotenv import load_dotenv
from lxml import etree
from tdf_pool.download import (
    download_webpage,
    get_overview_filepath,
)
from tdf_pool.stage import Stage

_logger = logging.getLogger(__name__)


class Race:
    def __init__(
        self,
        race_name: str,
        race_date: int | str,
        race_type: str,
        partial_url: str | None = None,
    ):
        self.name = race_name
        self.date = race_date
        self.race_type = race_type
        self._partial_url = partial_url

        self.stages = []
        self._get_stages()

    def _get_stages(self):
        if self.race_type == "1.UWT":
            self.stages = [
                Stage(
                    race_name=self.name,
                    stage_name=self.name,
                    stage_date=self.date,
                    stage_nr=1,
                    partial_url=self._partial_url,
                )
            ]
        elif self.race_type == "2.UWT":
            # Get overview page instead of final gc
            overview_page_link = (
                "https://www.procyclingstats.com/"
                + self._partial_url.replace("/gc", "")
            )
            download_webpage(
                overview_page_link,
                filepath=get_overview_filepath(self.name, self.date.year),
                strict=False,
            )

            # Get list of stages
            self._stage_list = list_multiday_race_stages(self.name, self.date.year)
            self.stages = [
                Stage(
                    race_name=self.name,
                    stage_name=stage["Name"],
                    stage_date=stage["Date"],
                    stage_nr=stage_nr + 1,
                    stage_type=stage["Type"],
                    partial_url=stage["PartialURL"],
                )
                for stage_nr, stage in self._stage_list.iterrows()
            ]

    def __repr__(self):
        return f"<Race: {self.name}, Date: {self.date}, number of stages: {len(self.stages)}>"


def list_multiday_race_stages(race, year):
    _logger.debug("[    ] Reading race overview page")
    overview_page = get_overview_filepath(race, year)
    with open(overview_page, "r", encoding="utf-8") as file:
        tree = etree.HTML(str(file.read()))
    _logger.debug("[ OK ] Read stage overview page")

    tables = tree.xpath("//table/../../h3[text()[contains(., 'Stages')]]/../span/table")
    if len(tables) != 1:
        raise ValueError("Stage table not found on race overview page")
    _logger.debug("[ OK ] Found Stage table")

    column_names = ["Date", "Day", "Profile", "Type", "Name", "PartialURL"]
    data = []
    for row in tables[0].xpath("tbody/tr")[:-1]:
        columns = row.xpath("td")

        # Extract data fields and convert
        stage_day, stage_month = columns[0].text.split("/")
        stage_date = date(year, int(stage_month), int(stage_day))
        if columns[3].text and columns[3].text == "Restday":
            data.append(
                [
                    stage_date,
                    stage_date.strftime("%A"),
                    None,
                    "Restday",
                    None,
                    None,
                ]
            )
        else:
            stage_day_of_week = columns[1].text
            stage_profile = columns[2].xpath("span")[0].attrib["class"]
            stage_description = columns[3].xpath("a")[0].text
            stage_prefix, stage_name = stage_description.split(" | ")
            if "(ITT)" in stage_prefix:
                stage_type = "ITT"
            elif "(TTT)" in stage_prefix:
                stage_type = "TTT"
            elif "Prologue" in stage_prefix:
                stage_type = "Prologue"
            elif "Stage" in stage_prefix:
                stage_type = "Stage"
            else:
                raise ValueError(
                    f"Can't extract stage type from stage prefix: {stage_prefix}"
                )
            stage_partial_url = columns[3].xpath("a")[0].attrib["href"]

            data.append(
                [
                    stage_date,
                    stage_day_of_week,
                    stage_profile,
                    stage_type,
                    stage_name,
                    stage_partial_url,
                ]
            )

    # Remove totals row
    race_stages = pd.DataFrame(data, columns=column_names)
    _logger.debug("[    ] Succesfully listed stages in race %s", race)
    return race_stages


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level="INFO")
    giro = Race(
        "Giro d'Italia", date(2023, 5, 6), "2.UWT", "race/giro-d-italia/2023/gc"
    )
    print(giro)
    print(giro._stage_list)
    print(
        Race(
            "Strade Bianche",
            date(2023, 3, 4),
            "1.UWT",
            "race/strade-bianche/2023/result",
        )
    )

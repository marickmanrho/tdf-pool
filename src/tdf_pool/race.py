import logging
from datetime import date
from typing import Literal

import pandas as pd
from dotenv import load_dotenv
from lxml import etree

from tdf_pool.download import (
    download_webpage,
    get_overview_filepath,
    get_startlist_filepath,
)
from tdf_pool.stage import Stage

_logger = logging.getLogger(__name__)


class Race:
    def __init__(
        self,
        race_name: str,
        race_date: date,
        race_type: Literal["1.UWT", "2.UWT"],
        partial_url: str,
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
                    stage_profile=stage["Profile"],
                    partial_url=stage["PartialURL"],
                )
                for stage_nr, stage in self._stage_list.iterrows()
            ]

    @property
    def startlist(self):
        # Get startlist page instead of final gc
        start_list_page_link = (
            "https://www.procyclingstats.com/"
            + self._partial_url.replace("/gc", "").replace("/result", "")
            + "/startlist"
        )
        print(start_list_page_link)
        download_webpage(
            start_list_page_link,
            filepath=get_startlist_filepath(self.name, self.date.year),
            strict=False,
        )

        startlist = list_riders(self.name, self.date.year)

        if "-" in startlist["BIB"]:
            teamname = ""
            bib = 0
            teamnr = 1
            for idx, row in startlist.iterrows():
                if row["Team"] != teamname:
                    teamname = row["Team"]
                    teamnr += 1
                    bib = 1
                startlist.loc[idx, "BIB"] = str(teamnr) + str(bib)
                bib += 1
        return startlist

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
            continue
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


def list_riders(race, year):
    _logger.debug("[    ] Reading race startlist page")
    startlist_filepath = get_startlist_filepath(race, year)
    with open(startlist_filepath, "r", encoding="utf-8") as file:
        tree = etree.HTML(str(file.read()))
    _logger.debug("[ OK ] Read startlist page")

    data = []

    teams = tree.xpath('//ul[contains(@class, "startlist_v4")]/li')
    for team_nr, team in enumerate(teams):
        teamname = team.xpath('div/div/a[contains(@class, "team")]')[0].text
        clean_teamname_parts = [
            s.translate(str.maketrans("", "", " \n\t\r")) for s in teamname.split(" ")
        ]
        clean_teamname = " ".join([s for s in clean_teamname_parts if s != ""])
        clean_teamname = clean_teamname.split("(")[0].strip()

        riders = team.xpath("div/ul/li")
        for rider_nr, rider in enumerate(riders):
            bib = rider.xpath('span[contains(@class, "bib")]')[0].text
            if bib == "":
                bib = str(team_nr) + str(rider_nr)
            name = rider.xpath("a")[0].text
            name_parts = [
                s.translate(str.maketrans("", "", " \n\t\r")) for s in name.split(" ")
            ]
            clean_name = " ".join([s for s in name_parts if s != ""])
            data.append((teamname, bib, clean_name))

    return pd.DataFrame(data, columns=["Team", "BIB", "Rider"])


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level="INFO")
    giro = Race(
        "Tour de France", date(2024, 6, 29), "2.UWT", "race/tour-de-france/2024"
    )
    # print(giro)
    print(giro.startlist)
    # print(
    #     Race(
    #         "Strade Bianche",
    #         date(2023, 3, 4),
    #         "1.UWT",
    #         "race/strade-bianche/2023/result",
    #     )
    # )

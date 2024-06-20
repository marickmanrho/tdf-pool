import logging

import pandas as pd
from dotenv import load_dotenv
from lxml import etree
from datetime import date
from tdf_pool.download import get_stage_filepath, download_webpage

_logger = logging.getLogger(__name__)


class Stage:
    def __init__(
        self,
        race_name: str,
        stage_name: str,
        stage_date: date,
        stage_nr: int | None = None,
        stage_type: str | None = None,
        partial_url: str | None = None,
    ):
        self.race_name = race_name
        self.stage_name = stage_name
        self.date = stage_date
        self.number = stage_nr
        self.type = stage_type
        self._partial_url = partial_url

        if partial_url is None:
            self.results = {}
        else:
            self._download_results()
            self._load_results()

    def _download_results(self):
        download_webpage(
            "https://www.procyclingstats.com/" + self._partial_url,
            filepath=get_stage_filepath(
                self.race_name, self.date.year, stage=self.number
            ),
            strict=False,
        )

    def _load_results(self):
        tree = get_stage_html_tree(self.race_name, self.date.year, self.number)
        self.results = read_stage_results(tree)

    @property
    def available_results(self) -> list[str]:
        return [str(k) for k in self.results.keys()]

    def __repr__(self):
        return f"<Race: {self.race_name}, Stage: {self.number}, Date: {self.date}, Type: {self.type}>"


def get_stage_html_tree(race: str, year: str | int, stage: int = 1) -> etree._Element:
    """Read the stage html file"""
    filepath = get_stage_filepath(race, year, stage)

    # Read HTML and construct lxml tree
    with open(filepath, "r", encoding="utf-8") as file:
        tree = etree.HTML(str(file.read()))

    _logger.debug("[ OK ] succesfully read %s", filepath)

    return tree


def parse_tab(tree: etree._Element, tab_name: str, tab_id: str) -> dict:
    """Parses a tab"""
    _logger.debug("[    ] parsing tab %s with id %s", tab_name, tab_id)
    # Parse subtab names
    tab = tree.xpath(
        f'//div[contains(@class, "result-cont") and contains(@data-id, "{tab_id}")]'
    )

    # For a given tab-id there may only be one div containing the results
    if len(tab) > 1:
        raise ValueError(f"found more than one result for data-id {tab_id}")
    tab = tab[0]

    # Get the list of subtabs
    subtab_list = tab.xpath('ul[contains(@class, "subsubResultNav")]/li/a')
    subtab_names = {"1": "General"}  # default subtab
    subtab_names.update({item.get("data-subtab"): item.text for item in subtab_list})

    # Read data from each subtab
    tab_data = {
        subtab_name: parse_subtab(tab, subtab_name, subtab_id)
        for subtab_id, subtab_name in subtab_names.items()
    }
    _logger.debug("[ OK ] succesfully parsed tab %s with id %s", tab_name, tab_id)
    return tab_data


def parse_subtab(tab: etree._Element, subtab_name: str, subtab_id: str):
    """Parses the tables on a subtab"""
    _logger.debug("[    ] parsing subtab %s with id %s", subtab_name, subtab_id)

    # All h3 elements are table names
    table_names = [
        item.text
        for item in tab.xpath(f'div[contains(@data-subtab, "{subtab_id}")]/h3')
    ]
    # Convert all table elements to pandas dataframes
    tables = [
        pd.read_html(etree.tostring(table, method="html"))[0]
        for table in tab.xpath(f'div[contains(@data-subtab, "{subtab_id}")]/table')
    ]

    for idx, table in enumerate(tables):
        if "Rider" not in table.columns:
            continue
        if len(table) == 0 or pd.isnull(table.loc[0, "Rider"]):
            _logger.debug(
                "[    ] Table %s subtab %s is empty, skipping", subtab_name, idx
            )
            continue
        for team_name in table["Team"].unique():
            table["Rider"] = (
                table["Rider"]
                .str.replace(team_name, "")
                .apply(lambda x: " ".join([c for c in str(x).split(" ") if c != ""]))
            )

        table["Rider"] = table["Rider"].str.strip()
        tables[idx] = table

    # A subtab may contain a single table without name
    if len(table_names) == 0:
        if len(tables) == 1:
            subtab_data = tables[0]
        else:
            raise ValueError("Found multiple tables without name.")
    else:
        subtab_data = dict(zip(table_names, tables))

    _logger.debug(
        "[ OK ] succesfully parsed subtab %s with id %s, found %s tables",
        subtab_name,
        subtab_id,
        len(tables),
    )
    return subtab_data


def read_stage_results(stage_tree: etree._Element) -> dict[str, pd.DataFrame]:
    """Extract the stage results from stage html"""

    # Parse tab names
    tab_list = stage_tree.xpath('//ul[contains(@class, "restabs")]/li/a')
    if len(tab_list) > 0:
        tab_names = {tab.get("data-id"): "".join(tab.itertext()) for tab in tab_list}

        _logger.debug("[    ] parsing tabs %s", tab_names)
        # Time trail stages have an empty string instead of Stage
        for tab_id, tab_name in tab_names.items():
            if tab_name == "":
                tab_names[tab_id] = "Stage"

        stage_data = {
            tab_name: parse_tab(stage_tree, tab_name, tab_id)
            for tab_id, tab_name in tab_names.items()
        }
    else:
        stage_data = {
            "Stage": {
                "General": pd.read_html(
                    etree.tostring(stage_tree.xpath("//table")[0], method="html")
                )[0]
            }
        }

    _logger.debug("[ OK ] succesfully parsed stage results")
    return stage_data


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level="DEBUG")
    tree = get_stage_html_tree("tour-de-france", 2019, 2)
    results = read_stage_results(tree)
    print(results["Stage"]["General"])

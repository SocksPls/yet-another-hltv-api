import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pprint
import re

# lib stuff
def get_team_id(soup):
    return soup.find("link", {"rel": "canonical"})["href"].split("/")[4]


def get_stats_url(soup):
    if soup.find("div", {"class": "stats-detailed-stats"}):
        return (
            "https://hltv.org"
            + soup.find("div", {"class": "stats-detailed-stats"}).select_one("a")[
                "href"
            ]
        )
    else:
        return None


def get_format(soup):
    # may not exist
    # see https://www.hltv.org/matches/2290099/mouz-vs-3dmax-esl-pro-series-germany-spring-2014-cup-1
    match_format = {}

    if soup.find("div", {"class": "preformatted-text"}):
        match_format["type"] = (
            soup.find("div", {"class": "preformatted-text"})
            .text.split("\n")[0]
            .split(" (")[0]
        )
        # location may not exist
        # see https://www.hltv.org/matches/2325765/mouz-vs-north-dreamhack-masters-stockholm-2018
        if "(" in soup.find("div", {"class": "preformatted-text"}).text.split("\n")[0]:
            match_format["location"] = (
                soup.find("div", {"class": "preformatted-text"})
                .text.split("\n")[0]
                .split(" (")[1][:-1]
            )
        else:
            match_format["location"] = None
    if match_format:
        return match_format
    else:
        return None


def get_significance(soup):
    if soup.find("div", {"class": "preformatted-text"}):
        return (
            soup.find("div", {"class": "preformatted-text"})
            .text.splitlines()[-1][1:]
            .strip()
        )
    else:
        return None


def get_match_status(soup):
    # scheduled matches have a countdown timer instead of parsable text
    match_status = "Scheduled"
    status_text = soup.find("div", {"class": "countdown"}).text.strip()
    if status_text == "LIVE":
        match_status = "LIVE"
    if status_text == "Match postponed":
        match_status = "Postponed"
    if status_text == "Match deleted":
        match_status = "Deleted"
    if status_text == "Match over":
        match_status = "Over"

    return match_status


def get_stats_id(soup):
    if (
        soup.find("div", {"class": "stats-detailed-stats"})
        and "mapstats"
        not in soup.find("div", {"class": "stats-detailed-stats"}).find("a")["href"]
    ):
        return (
            soup.find("div", {"class": "stats-detailed-stats"})
            .find("a")["href"]
            .split("/")[3]
        )


def get_team(soup, team):
    if (
        soup.find("div", {"class": f"team{team}-gradient"})
        and soup.find("div", {"class": f"team{team}-gradient"}).text.strip()
    ):
        return {
            "name": soup.find("div", {"class": f"team{team}-gradient"})
            .find("div", {"class": "teamName"})
            .text,
            "id": soup.find("div", {"class": "team1-gradient"})
            .select_one("a")["href"]
            .split("/")[2],
        }
    else:
        return None


def get_vetoes(soup):
    vetoes = []

    # New Format
    # len > 1 as format box also has veto-box class
    if len(soup.find_all("div", {"class": "veto-box"})) > 1:
        for veto in (
            soup.find_all("div", {"class": "veto-box"})[-1]
            .find("div", {"class": "padding"})
            .find_all("div")
        ):
            veto = veto.text[3:]

            try:
                # this mess is to support teams with spaces in the name (eg. MAD Lions)
                team_name, map_name = re.split(r"removed|picked", veto)
                team_name = team_name.strip()
                map_name = map_name.strip()

                vetoes.append(
                    {
                        "team": team_name,
                        "type": "picked" if "picked" in veto else "removed",
                        "map": map_name,
                    }
                )

            except ValueError:
                if veto.endswith("was left over"):
                    vetoes.append(
                        {
                            "team": None,
                            "type": "leftover",
                            "map": veto.split(" ")[0],
                        }
                    )

    # Old Format
    # see https://www.hltv.org/matches/2300113/mouz-vs-north-dreamhack-masters-stockholm-2018
    if soup.find_all("div", {"class": "veto-box"}):
        lines = soup.find_all("div", {"class": "veto-box"})[0].text.split("\n")
        veto_index = None
        for index, line in enumerate(lines):
            if "Veto process" in line:
                veto_index = index
        if veto_index:
            for line in lines[veto_index + 2 : -1]:
                veto = line[3:]
                if veto.endswith("was left over"):
                    vetoes.append(
                        {
                            "team": None,
                            "type": "leftover",
                            "map": veto.split(" ")[0],
                        }
                    )
                else:
                    vetoes.append(
                        {
                            "team": veto.split(" ")[0],
                            "type": veto.split(" ")[1],
                            "map": veto.split(" ")[2],
                        }
                    )

    if vetoes:
        return vetoes
    else:
        return None


def get_event(soup):
    return {
        "name": soup.find("div", {"class": ["timeAndEvent", "event"]}).find("a").text,
        "id": soup.find("div", {"class": ["timeAndEvent", "event"]})
        .find("a")["href"]
        .split("/")[2],
    }


def get_community_odds(soup):
    # get community odds. will not exist for past games but do exist for live games
    community_odds = {}
    if soup.find("div", {"class": "pick-a-winner"}):
        community_odds["provider"] = "community"
        community_odds["team1"] = (
            soup.find("div", {"class": "pick-a-winner"})
            .find("div", {"class": "team1"})
            .find("div", {"class": "percentage"})
            .text.replace("%", "")
        )
        community_odds["team2"] = (
            soup.find("div", {"class": "pick-a-winner"})
            .find("div", {"class": "team2"})
            .find("div", {"class": "percentage"})
            .text.replace("%", "")
        )

    if community_odds:
        return community_odds
    else:
        return None


def get_maps(soup):

    maps = []

    # if maps are not announced these divs will say "TBA"
    for map_result in soup.find_all("div", {"class": "mapholder"}):

        # return None if maps are not yet announced
        if map_result.find("div", {"class": "mapname"}).text == "TBA":
            return None

        if map_result.find("div", {"class": "results-left"}) and map_result.find(
            "span", {"class": "results-right"}
        ):
            # map scores announced, get scores
            map_scores = {
                "name": map_result.find("div", {"class": "mapname"}).text,
                "result": {
                    "team1_total_rounds": int(
                        map_result.find("div", {"class": "results-left"})
                        .find("div", {"class": "results-team-score"})
                        .text.strip()
                    )
                    if map_result.find("div", {"class": "results-left"})
                    .find("div", {"class": "results-team-score"})
                    .text.strip()
                    != "-"
                    else None,
                    "team2_total_rounds": int(
                        map_result.find("span", {"class": "results-right"})
                        .find("div", {"class": "results-team-score"})
                        .text.strip()
                    )
                    if map_result.find("span", {"class": "results-right"})
                    .find("div", {"class": "results-team-score"})
                    .text.strip()
                    != "-"
                    else None,
                },
            }

            # stats won't exist for games in progress or upcoming
            if map_result.find("a", {"class": "results-stats"}):
                map_scores["stats_id"] = map_result.find(
                    "a", {"class": "results-stats"}
                )["href"].split("/")[4]
                map_scores["stats_url"] = (
                    "https://hltv.org"
                    + map_result.find("a", {"class": "results-stats"})["href"]
                )
            else:
                map_scores["stats_id"] = None
                map_scores["stats_url"] = None

            # i guess no results will exist for upcoming games
            # TODO: only check halftime score if full score exists

            if map_result.find("div", {"class": "results-center-half-score"}):
                halves_raw = (
                    map_result.find("div", {"class": "results-center-half-score"})
                    .text.strip()
                    .replace(";", "")
                    .replace("(", "")
                    .replace(")", "")
                    .split(" ")
                )
                map_scores["result"]["half_results"] = []
                for half in halves_raw:
                    half = half.split(":")
                    map_scores["result"]["half_results"].append(
                        {
                            "team1_rounds": int(half[0]) if half[0] != "-" else None,
                            "team2_rounds": int(half[1]) if half[1] != "-" else None,
                        }
                    )
            elif False:
                map_scores["result"]["half_results"] = None

            if map_scores["result"] == {
                "team1_total_rounds": None,
                "team2_total_rounds": None,
            }:
                map_scores["result"] = None
        else:

            # map has no results
            # eg https://www.hltv.org/matches/2290099/mouz-vs-3dmax-esl-pro-series-germany-spring-2014-cup-1
            map_scores = {
                "name": map_result.find("div", {"class": "mapname"}).text,
                "result": None,
                "stats_id": None,
                "stats_url": None,
            }

        if map_scores:
            maps.append(map_scores)

    return maps


def get_players(soup):
    players = {"team1": [], "team2": []}
    if soup.find_all("div", {"class": "players"}):
        for player in (
            soup.find_all("div", {"class": "players"})[0]
            .find_all("tr")[-1]
            .find_all("div", {"class": "flagAlign"})
        ):
            players["team1"].append(
                {
                    "name": player.find("div", {"class": "text-ellipsis"}).text,
                    "id": player["data-player-id"],
                }
            )

        for player in (
            soup.find_all("div", {"class": "players"})[1]
            .find_all("tr")[-1]
            .find_all("div", {"class": "flagAlign"})
        ):
            players["team2"].append(
                {
                    "name": player.find("div", {"class": "text-ellipsis"}).text,
                    "id": player["data-player-id"],
                }
            )
        return players
    else:
        return None


def get_streams(soup):
    # only exists for live or upcoming games
    streams = []
    for box in soup.find_all("div", {"class": "stream-box"}):
        if box.find("img", {"class": "stream-flag"}) and box.find(
            "div", {"class": "stream-box-embed"}
        ):
            streams.append(
                {
                    "name": box.find("div", {"class": "stream-box-embed"}).text,
                    "link": box.find("div", {"class": "stream-box-embed"})[
                        "data-stream-embed"
                    ],
                    "viewers": int(
                        box.find("span", {"class": "gtSmartphone-only"}).text
                    ),
                }
            )
        elif "hltv-live" in box.get("class"):
            streams.append(
                {
                    "name": "HLTV Live",
                    "link": "https://hltv.org" + box.select_one("a")["href"],
                    "viewers": -1,
                }
            )
        elif "gotv" in box.get("class"):
            streams.append(
                {"name": "GOTV", "link": box.text.split('"')[1], "viewers": -1}
            )

    if streams:
        return streams
    else:
        return None


def get_demo(soup):
    if (
        soup.find_all("div", {"class": "stream-box"})
        and soup.find("div", {"class": "stream-box"}).text == "GOTV Demo"
    ):
        return (
            "https://hltv.org"
            + soup.find_all("div", {"class": "stream-box"})[0].find("a")["href"]
        )
    else:
        return None


def get_winner_team(soup, team1=None, team2=None):
    if team1 and team2:
        if bool(
            soup.find("div", {"class": "team1-gradient"}).find("div", {"class": "won"})
        ):
            return team1
        elif bool(
            soup.find("div", {"class": "team2-gradient"}).find("div", {"class": "won"})
        ):
            return team2
        else:
            return None
    else:
        return None


def get_match(soup):
    match = {
        "title": soup.find("div", {"class": "timeAndEvent"}).text.strip(),
        "date": datetime.fromtimestamp(
            int(
                soup.find("div", {"class": "timeAndEvent"}).find(
                    "div", {"class": "date"}
                )["data-unix"]
            )
            / 1000
        ),
        "format": get_format(soup),
        "significance": get_significance(soup),
        "status": get_match_status(soup),
        "has_scorebot": bool(soup.find("div", {"id": "scoreboardElement"})),
        "stats_id": get_stats_id(soup),
        "team1": get_team(soup, 1),
        "team2": get_team(soup, 2),
        "vetoes": get_vetoes(soup),
        "event": get_event(soup),
        # non-community odds coming soon(tm)
        "odds": get_community_odds(soup),
        "maps": get_maps(soup),
        "players": get_players(soup),
        "streams": get_streams(soup),
        "demos": get_demo(soup),
    }
    if match["team1"] and match["team2"]:
        match["winner_team"] = get_winner_team(soup, match["team1"], match["team2"])
    else:
        match["winner_team"] = None

    return match


# demo stuff
def get_soup(url):
    headers = {
        "referer": "https://www.hltv.org/stats",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    cookies = {"hltvTimeZone": "Europe/Copenhagen"}

    return BeautifulSoup(
        requests.get(url, headers=headers, cookies=cookies).text, "lxml"
    )


if __name__ == "__main__":
    pprint.pprint(get_match(get_soup(input("Enter Match URL\n> "))))

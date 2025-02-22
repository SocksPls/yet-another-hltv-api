import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pprint
import re
import urllib3
import get_soup


def get_player(soup):
    player = {
        # basic info available for all players
        "id": int(soup.find("meta", {"property": "og:url"})["content"].split("/")[4]),
        "nickname": soup.find("h1", {"class": "playerNickname"}).text.strip(),
        "team_name": soup.find("div", {"class": "playerTeam"})
        .find("span", {"class": "listRight"})
        .text.strip(),
    }

    # shows "-" if unavailable: https://www.hltv.org/player/24300/buddy
    player["real_name"] = soup.find("div", {"class": "playerRealname"}).text.strip()

    if player["team_name"].lower() != "no team":
        # get team id
        player["team_id"] = int(
            soup.find("div", {"class": "playerTeam"})
            .find("span", {"class": "listRight"})
            .a["href"]
            .split("/")[2]
        )
    else:
        # no team, set team id 0
        player["team_id"] = 0

    player["benched"] = bool("benched" in player["team_name"].lower())

    age = (
        soup.find("div", {"class": "playerAge"})
        .find("span", {"class": "listRight"})
        .text.split(" ")[0]
    )
    if age.isnumeric():
        player["age"] = int(age)
    else:
        player["age"] = None

    return player


if __name__ == "__main__":
    pprint.pprint(
        get_player(get_soup.get_soup("https://www.hltv.org/player/7998/s1mple"))
    )

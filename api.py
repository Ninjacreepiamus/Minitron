from adafruit_requests import Session
from socketpool import SocketPool
from ssl import create_default_context
import json

# ESPN API websites
mlb_url = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
nba_url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
nfl_url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ncaab_url = "http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"

def extract_baseball(pool):
    baseball_games = []
    requests = Session(pool, create_default_context())
    
    try:
        print("Requesting from API...")
        response = requests.get(mlb_url)
    except:
        print("Website does not work....")
        return

    json_response = response.json()

    for i in range(len(json_response["events"])): # len(json_response["events"])
        game = json_response["events"][i]
        
        home_team = game["competitions"][0]["competitors"][0]["team"]["abbreviation"]
        away_team = game["competitions"][0]["competitors"][1]["team"]["abbreviation"]
        home_color_main = game["competitions"][0]["competitors"][0]["team"].get("color", '000000')
        home_color_alt = game["competitions"][0]["competitors"][0]["team"].get("alternateColor", '000000')
        away_color_main = game["competitions"][0]["competitors"][1]["team"].get("color", '000000')
        away_color_alt = game["competitions"][0]["competitors"][1]["team"].get("alternateColor", '000000')     
        home_score = game["competitions"][0]["competitors"][0]["score"]
        away_score = game["competitions"][0]["competitors"][1]["score"]
        inning = game["competitions"][0]["status"]["type"].get("shortDetail", "0")
        
        if "situation" in game["competitions"][0]:
            first = game["competitions"][0]["situation"].get("onFirst", False)
            second = game["competitions"][0]["situation"].get("onSecond", False)
            third = game["competitions"][0]["situation"].get("onThird", False)
            balls = game["competitions"][0]["situation"].get("balls", 0)
            strikes = game["competitions"][0]["situation"].get("strikes", 0)
            outs = game["competitions"][0]["situation"].get("outs", 0)
        else:
            first = second = third = False
            balls = strikes = outs = 0

        baseball_game_dict = {
            "HOME": home_team,
            "AWAY": away_team,
            "HOME_COLOR_MAIN" : home_color_main,
            "HOME_COLOR_ALT" : home_color_alt,
            "AWAY_COLOR_MAIN" : away_color_main,
            "AWAY_COLOR_ALT": away_color_alt,
            "HOME_SCORE": home_score,
            "AWAY_SCORE": away_score,
            "INNING": inning,
            "ON_FIRST": first,
            "ON_SECOND": second,
            "ON_THIRD": third,
            "BALLS" : balls,
            "STRIKES" : strikes,
            "OUTS" : outs
        }
        baseball_games.append(baseball_game_dict)

    with open("baseball.json", "w") as f2:
        json.dump(baseball_games, f2)
    f2.close()
    return baseball_games

def extract_basketball(pool):
    basketball_games = []
    requests = Session(pool, create_default_context())
    
    try:
        print("Requesting Basketball Games...")
        response = requests.get(nba_url)
    except:
        print("Website does not work....")
        return

    json_response = response.json()

    for i in range(len(json_response["events"])): # len(json_response["events"])
        game = json_response["events"][i]
        home_team = game["competitions"][0]["competitors"][0]["team"]["abbreviation"]
        away_team = game["competitions"][0]["competitors"][1]["team"]["abbreviation"]
        home_color_main = game["competitions"][0]["competitors"][0]["team"].get("color", '000000')
        home_color_alt = game["competitions"][0]["competitors"][0]["team"].get("alternateColor", '000000')
        away_color_main = game["competitions"][0]["competitors"][1]["team"].get("color", '000000')
        away_color_alt = game["competitions"][0]["competitors"][1]["team"].get("alternateColor", '000000')
        home_score = game["competitions"][0]["competitors"][0]["score"]
        away_score = game["competitions"][0]["competitors"][1]["score"]
        quarter = game["competitions"][0]["status"]["period"]
        finished = game["competitions"][0]["status"]["type"]["completed"]
       
        basketball_game_dict = {
            "HOME": home_team,
            "AWAY": away_team,
            "HOME_COLOR_MAIN" : home_color_main,
            "HOME_COLOR_ALT" : home_color_alt,
            "AWAY_COLOR_MAIN" : away_color_main,
            "AWAY_COLOR_ALT": away_color_alt,
            "HOME_SCORE": home_score,
            "AWAY_SCORE": away_score,
            "QUARTER": quarter,
            "FINISHED": finished
        }

        # print(basketball_game_dict)
        basketball_games.append(basketball_game_dict)

    with open("basketball.json", "w") as f2:
        json.dump(basketball_games, f2)
    f2.close()
    return basketball_games

def extract_ncaab(pool):
    ncaab_games = []
    requests = Session(pool, create_default_context())
    
    try:
        print("Requesting Basketball Games...")
        response = requests.get(ncaab_url)
    except:
        print("Website does not work....")
        return

    json_response = response.json()

    for i in range(len(json_response["events"])): # len(json_response["events"])
        game = json_response["events"][i]
        home_team = game["competitions"][0]["competitors"][0]["team"]["abbreviation"]
        away_team = game["competitions"][0]["competitors"][1]["team"]["abbreviation"]
        home_color_main = game["competitions"][0]["competitors"][0]["team"].get("color", '000000')
        home_color_alt = game["competitions"][0]["competitors"][0]["team"].get("alternateColor", '000000')
        away_color_main = game["competitions"][0]["competitors"][1]["team"].get("color", '000000')
        away_color_alt = game["competitions"][0]["competitors"][1]["team"].get("alternateColor", '000000')
        home_score = game["competitions"][0]["competitors"][0]["score"]
        away_score = game["competitions"][0]["competitors"][1]["score"]
        quarter = game["competitions"][0]["status"]["period"]
        finished = game["competitions"][0]["status"]["type"]["completed"]
       
        ncaab_game_dict = {
            "HOME": home_team,
            "AWAY": away_team,
            "HOME_COLOR_MAIN" : home_color_main,
            "HOME_COLOR_ALT" : home_color_alt,
            "AWAY_COLOR_MAIN" : away_color_main,
            "AWAY_COLOR_ALT": away_color_alt,
            "HOME_SCORE": home_score,
            "AWAY_SCORE": away_score,
            "QUARTER": quarter,
            "FINISHED": finished
        }

        # print(basketball_game_dict)
        ncaab_games.append(ncaab_game_dict)

    with open("ncaab.json", "w") as f2:
        json.dump(ncaab_games, f2)
    f2.close()
    return ncaab_games

def extract_football(pool):
    football_games = []
    requests = Session(pool, create_default_context())
    
    try:
        response = requests.get(nfl_url)
    except:
        print("Website does not work....")
        return

    json_response = response.json()

    for i in range(len(json_response["events"])): # len(json_response["events"])
        game = json_response["events"][i]
        home_team = game["competitions"][0]["competitors"][0]["team"].get("abbreviation", "N/A")
        away_team = game["competitions"][0]["competitors"][1]["team"].get("abbreviation", "N/A")
        home_color_main = game["competitions"][0]["competitors"][0]["team"].get("color", 'ff0000')
        home_color_alt = game["competitions"][0]["competitors"][0]["team"].get("alternateColor", '000000')
        away_color_main = game["competitions"][0]["competitors"][1]["team"].get("color", '0000ff')
        away_color_alt = game["competitions"][0]["competitors"][1]["team"].get("alternateColor", '000000')
        home_score = game["competitions"][0]["competitors"][0].get("score", "N/A")
        away_score = game["competitions"][0]["competitors"][1].get("score", "N/A")
        quarter = game["competitions"][0]["status"].get("period", "N/A")
        finished = game["competitions"][0]["status"]["type"].get("completed", False)
   
        football_game_dict = {
            "HOME": home_team,
            "AWAY": away_team,
            "HOME_COLOR_MAIN" : home_color_main,
            "HOME_COLOR_ALT" : home_color_alt,
            "AWAY_COLOR_MAIN" : away_color_main,
            "AWAY_COLOR_ALT": away_color_alt,
            "HOME_SCORE": home_score,
            "AWAY_SCORE": away_score,
            "QUARTER": quarter,
            "FINISHED": finished
        }
       
        football_games.append(football_game_dict)
   
    with open("football.json", "w") as f2:
        json.dump(football_games, f2)
    
    f2.close()
    return football_games
# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_display_text.label import Label
from adafruit_display_text.scrolling_label import ScrollingLabel
from adafruit_display_shapes.rect import Rect
import board
from displayio import Group, release_displays, OnDiskBitmap, TileGrid, ColorConverter
from framebufferio import FramebufferDisplay
from rgbmatrix import RGBMatrix
from terminalio import FONT
from time import sleep
from adafruit_datetime import datetime
from digitalio import DigitalInOut, Pull
from rtc import RTC, set_time_source
import asyncio
from adafruit_requests import Session
from ssl import create_default_context
from wifi import radio
from socketpool import SocketPool
import adafruit_ntp
from gc import collect
from storage import remount
import json
import string
import re
import math
from api import *

#Color palatte
WHITE = 0xffffff
BLACK = 0x000000
RED = 0xff0000
GREEN = 0x00ff00
BLUE = 0x0000ff
CYAN = 0x00ffff
YELLOW = 0xffff00
MAGENTA = 0xff00ff
GAME_STAGNANT = 0x8c1919
GAME_HOVERED = YELLOW

# Initializing Pins
L_button = DigitalInOut(board.IO5) #PIN0
R_button = DigitalInOut(board.IO21) #PIN12
SELECT_button = DigitalInOut(board.IO42) #PIN13
BACK_button = DigitalInOut(board.IO16) #PIN11

L_button.pull = Pull.UP
R_button.pull = Pull.UP
SELECT_button.pull = Pull.UP
BACK_button.pull = Pull.UP

clock_color = GREEN
games = []
ssid = None
password = None

wifi_small_bmp = OnDiskBitmap(open("bitmaps/wifi_small.bmp", "rb"))
wifi_small_tilegrid = TileGrid(
    wifi_small_bmp,
    pixel_shader=getattr(wifi_small_bmp, 'pixel_shader', ColorConverter()),
    tile_width=9,
    tile_height=9,
    x=0,
    y=23,
)
wifi_small_tilegrid.hidden = True

api_bmp = OnDiskBitmap(open("bitmaps/api.bmp", "rb"))
api_tilegrid = TileGrid(
    api_bmp,
    pixel_shader=getattr(api_bmp, 'pixel_shader', ColorConverter()),
    tile_width=13,
    tile_height=5,
    x=51,
    y=27,
)
api_tilegrid.hidden = True

# Initializing States
MENU = 3
NFL = 0
MLB = 1
NBA = 2
NCAAB = 4
CLOCK = 5
state = CLOCK

pool = SocketPool(radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=-5)

def rstrip(s, chars=None):
    """
    Return a copy of the string with trailing whitespace removed.

    If chars is given and not None, remove characters in chars instead.
    """
    if chars is None:
        chars = "\t\n\r\f\v\x00"  # Default whitespace characters

    end = len(s)
    while end > 0 and s[end - 1] in chars:
        end -= 1

    return s[:end]

def plus_to_spaces(string):
    new = ''
    for c in string:
        if c == '+':
            new = new + ' '
        else:
            new = new + c
    return new

# Takes 'Final' or 'Bot 2nd' or 'Day and Time' and strips for time only
def inning_format(input_string):
    output_pattern = re.compile(r'\d+:\d+\s*(AM|PM)')
    output_search = output_pattern.search(input_string)
    if output_search:
        return output_search.group(0)  # Access the first captured group
    else:
        return input_string

# Takes 'Bot 2nd' or 'Top 2nd' and gives '2nd'
def inning_number(input_string):
    # Top of the inning is True, bottom is False
    output_pattern = re.compile(r'^Top\s*(.*)')
    output_search = output_pattern.search(input_string)
    if output_search:
        return output_search.group(1)
    
    output_pattern = re.compile(r'^Bot\s*(.*)')
    output_search = output_pattern.search(input_string)
    if output_search:
        return output_search.group(1)
    
    # If neither "Top" nor "Bot" is found, assume it's top by default
    return input_string

# Takes 'Top #' or 'Bot #' and gives true if Top, false if Bottom (used for arrow icon)
def top_or_bottom(input_string):
    output_pattern = re.compile(r'^Bot\s*(.*)')
    output_search = output_pattern.search(input_string)
    if output_search:
        return False
    else:
        return True
    
def hex_to_rgb(hex_string):
    """Convert hex string to RGB tuple."""
    hex_string = hex_string.lstrip('#')
    return tuple(int(hex_string[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_tuple):
    """Convert RGB tuple to hexadecimal integer."""
    hex_string = '{:02x}{:02x}{:02x}'.format(*rgb_tuple)
    return int(hex_string, 16)  # Return hexadecimal integer

def brightness(color):
    """Calculate brightness of a color."""
    r, g, b = color
    return (r * 299 + g * 587 + b * 114) / 1000

def color_distance(color1, color2):
    """Calculate Euclidean distance between two colors in RGB space."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5

def string_to_hex(hex_string):
    color_int = int(hex_string.lstrip('#'), 16)
    return hex(color_int)  # Output: 0xffb612

def find_best_color_combo(home_main, home_alt, away_main, away_alt):
    home_main_rgb = hex_to_rgb(home_main)
    home_alt_rgb = hex_to_rgb(home_alt)
    away_main_rgb = hex_to_rgb(away_main)
    away_alt_rgb = hex_to_rgb(away_alt)

    home_colors = [home_main_rgb, home_alt_rgb]
    away_colors = [away_main_rgb, away_alt_rgb]

    best_away = None
    best_home = None
    best_distance = float('inf')
    
    for away_color in away_colors:
        for home_color in home_colors:
            # Check if any color is too close to black
            if brightness(away_color) < 50 or brightness(home_color) < 50:
                continue
                
            # Check if colors are too close to each other
            if color_distance(away_color, home_color) < 100:
                continue
                
            # Calculate distance between away and home colors
            distance = color_distance(away_color, home_color)
            
            # Update best combo if distance is smaller
            if distance < best_distance:
                best_distance = distance
                best_away = away_color
                best_home = home_color
    
    # If no suitable combination is found, use emergency color (white)
    if best_away is None or best_home is None:
        return 0xffffff, 0xffffff  # Return hexadecimal integer

    return rgb_to_hex(best_home), rgb_to_hex(best_away)
    
def init_Display():
    release_displays()
    matrix = RGBMatrix(
        width=64,
        bit_depth=2,
        rgb_pins=[board.IO7, board.IO8, board.IO9, board.IO10, board.IO11, board.IO12],
        addr_pins=[board.A0, board.A1, board.A2, board.A3],
        clock_pin=board.IO13,
        latch_pin=board.IO15,
        output_enable_pin=board.IO14,
    )
    display = FramebufferDisplay(matrix)

    return display

def init_RTC():
    rtcobj = RTC()
    if radio.connected == False:
        pass
    else:
        rtcobj.datetime = ntp.datetime
    set_time_source(rtcobj)
    return rtcobj

def init_WIFI(ssid, password):    
    print(f'Conn: {ssid}')
    try:
        radio.connect(ssid, password)
        print("Success  ")
        pool = SocketPool(radio)
        ntp = adafruit_ntp.NTP(pool, tz_offset=-4)
    except Exception as e:
        print(f'Failure: {e}')

    return init_RTC()

FORM_SUBMITTED_FLAG = 1

def find_WIFI():
    # Set up the ESP32's network interface
    radio.start_ap("MinitronAccess", password="123456789")  # Set your desired AP name and password
    pool = SocketPool(radio)  # Initialize socket pool

    # Access Point started. Waiting for a connection
    print('192.168.4.1')

    # Initialize form_submitted_flag outside the while loop
    form_submitted_flag = False

    # Set up the server socket
    server_sock = pool.socket()
    server_sock.bind(("0.0.0.0", 80))
    server_sock.listen(1)

    # Main loop
    while True:
        try:
            # Accept a connection and get the client socket and address
            client, addr = server_sock.accept()
            print("Client connected from", addr)

            # Set the client socket to non-blocking mode
            client.setblocking(False)

            # Read the HTTP request data
            buffer_size = 1024
            request_data = bytearray(buffer_size)

            try:
                num_bytes_received = client.recv_into(request_data, buffer_size)
                print("Request data:", request_data[:num_bytes_received].decode("utf-8"))

                # Check if the form has been submitted
                if b"POST /submit" in request_data:
                    # Extract SSID and Password from the form submission
                    ssid_start = request_data.find(b"ssid=") + 5
                    ssid_end = request_data.find(b"&", ssid_start)
                    ssid = request_data[ssid_start:ssid_end].decode("utf-8")

                    password_start = request_data.find(b"password=") + 9
                    password_end = request_data.find(b" ", password_start)
                    password = rstrip(request_data[password_start:password_end].decode("utf-8"))

                    # Set the form submitted flag
                    form_submitted_flag = True

            except Exception as e:
                print("Error handling request:", e)

            finally:
                # Serve the form if it has not been submitted
                if not form_submitted_flag:
                    # Send an HTTP response with a form for entering SSID and password
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/html\r\n\r\n"
                        "<html><body>"
                        "<h2>Enter WiFi Credentials</h2>"
                        '<form action="/submit" method="post">'
                        'SSID: <input type="text" name="ssid"><br>'
                        'Password: <input type="password" name="password"><br>'
                        '<input type="submit" value="Submit">'
                        '</form>'
                        "</body></html>"
                    )
                    client.send(response)

                # Close the client connection
                client.close()

                # Restart the access point if the form is submitted
                if form_submitted_flag:
                    print("Form submitted. Waiting before restarting Access Point...")
                    sleep(5)  # Adjust the delay as needed
                    # print("Restarting Access Point...")
                    radio.stop_ap()  # Stop the AP before starting it again
                    print('Stopped access point')
                    return plus_to_spaces(ssid), password
        except Exception as e:
            print("Error:", e)     

def display_Menu(display):
    # Position Counter
    position = 0

    # Load BMP image, create Group and TileGrid to hold it
    nfl_filename = "bitmaps/nfl.bmp"
    mlb_filename = "bitmaps/mlb.bmp"
    nba_filename = "bitmaps/nba.bmp"
    ncaab_filename = "bitmaps/ncaab.bmp"

    # CircuitPython 6 & 7 compatible
    nfl_bitmap = OnDiskBitmap(open(nfl_filename, "rb"))
    nfl_tilegrid = TileGrid(
        nfl_bitmap,
        pixel_shader=getattr(nfl_bitmap, 'pixel_shader', ColorConverter()),
        tile_width=17,
        tile_height=17,
        x=3,
        y=2
    )
    
    mlb_bitmap = OnDiskBitmap(open(mlb_filename, "rb"))
    mlb_tilegrid = TileGrid(
        mlb_bitmap,
        pixel_shader=getattr(mlb_bitmap, 'pixel_shader', ColorConverter()),
        tile_width=17,
        tile_height=17,
        x=24,
        y=2
    )
    
    nba_bitmap = OnDiskBitmap(open(nba_filename, "rb"))
    nba_tilegrid = TileGrid(
        nba_bitmap,
        pixel_shader=getattr(nba_bitmap, 'pixel_shader', ColorConverter()),
        tile_width=17,
        tile_height=17,
        x=45,
        y=2
    )

    ncaab_bitmap = OnDiskBitmap(open(ncaab_filename, "rb"))
    ncaab_tilegrid = TileGrid(
        ncaab_bitmap,
        pixel_shader=getattr(ncaab_bitmap, 'pixel_shader', ColorConverter()),
        tile_width=17,
        tile_height=17,
        x=8,
        y=2
    )
    
    
    nfl_text = Label(
    FONT,
    color=MAGENTA,
    text="NFL")
    nfl_text.x = 3
    nfl_text.y = 24
    
    mlb_text = Label(
    FONT,
    color=RED,
    text="MLB")
    mlb_text.x = 24
    mlb_text.y = 24
    
    nba_text = Label(
    FONT,
    color=RED,
    text="NBA")
    nba_text.x = 45
    nba_text.y = 24
    
    ncaab_text = Label(
    FONT,
    color=MAGENTA,
    text="NCAAB")
    ncaab_text.x = 3
    ncaab_text.y = 24

    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(nfl_tilegrid)
    group.append(mlb_tilegrid)
    group.append(nba_tilegrid)
    group.append(nfl_text)
    group.append(mlb_text)
    group.append(nba_text)
    display.show(group)
    display.refresh()
    sleep(0.4) # Debounce

    while True:
        # Internet Interrupt
        if radio.connected is False:
            wifi_small_tilegrid.hidden is False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        
        # R Button Press
        if (R_button.value == False):
            if position == NFL:
                nfl_text.color = RED
                mlb_text.color = MAGENTA
                nba_text.color = RED
                position = MLB
            elif position == MLB:
                nfl_text.color = RED
                mlb_text.color = RED
                nba_text.color = MAGENTA
                position = NBA
            elif position == NBA:
                group.append(ncaab_tilegrid)
                group.append(ncaab_text)
                group.remove(nfl_tilegrid)
                group.remove(mlb_tilegrid)
                group.remove(nba_tilegrid)
                group.remove(nfl_text)
                group.remove(mlb_text)
                group.remove(nba_text)
                display.refresh()
                position = NCAAB

            elif position == NCAAB:
                nfl_text.color = MAGENTA
                mlb_text.color = RED
                nba_text.color = RED
                group.remove(ncaab_tilegrid)
                group.remove(ncaab_text)
                group.append(nfl_tilegrid)
                group.append(mlb_tilegrid)
                group.append(nba_tilegrid)
                group.append(nfl_text)
                group.append(mlb_text)
                group.append(nba_text)
                display.refresh()
                position = NFL
            sleep(0.4)
        
        # L Button Press
        elif (L_button.value == False):
            if position == NFL:
                group.append(ncaab_tilegrid)
                group.append(ncaab_text)
                group.remove(nfl_tilegrid)
                group.remove(mlb_tilegrid)
                group.remove(nba_tilegrid)
                group.remove(nfl_text)
                group.remove(mlb_text)
                group.remove(nba_text)
                display.refresh()
                position = NCAAB
            elif position == MLB:
                nfl_text.color = MAGENTA
                mlb_text.color = RED
                nba_text.color = RED
                position = NFL
            elif position == NBA:
                nfl_text.color = RED
                mlb_text.color = MAGENTA
                nba_text.color = RED
                position = MLB
            elif position == NCAAB:
                nfl_text.color = RED
                mlb_text.color = RED
                nba_text.color = MAGENTA
                group.remove(ncaab_tilegrid)
                group.remove(ncaab_text)
                group.append(nfl_tilegrid)
                group.append(mlb_tilegrid)
                group.append(nba_tilegrid)
                group.append(nfl_text)
                group.append(mlb_text)
                group.append(nba_text)
                display.refresh()
                position = NBA
            sleep(0.4)
        
        elif (BACK_button.value == False):
            sleep(0.4)
            group.remove(wifi_small_tilegrid)
            return CLOCK
           
        elif (SELECT_button.value == False):
            sleep(0.4)
            group.remove(wifi_small_tilegrid)
            return position
    

def display_GAMES(display, rtcobj):
    global games
    game_position = 0
    
    if not games:
        if state == MLB:
            if radio.connected == True:
                games = extract_baseball(pool)
            else:
                f = open("baseball.json", "r")
                games = json.load(f)
                f.close()
        elif state == NFL:
            if radio.connected == True:
                games = extract_football(pool)
            else:
                f = open("football.json", "r")
                games = json.load(f)
                f.close()
        elif state == NBA:
            if radio.connected == True:
                games = extract_basketball(pool)
            else:
                f = open("basketball.json", "r")
                games = json.load(f)
                f.close()
        elif state == NCAAB:
            if radio.connected == True:
                games = extract_ncaab(pool)
            else:
                f = open("ncaab.json", "r")
                games = json.load(f)
                f.close()
    
    game1_text = ScrollingLabel(
    FONT,
    color=GAME_STAGNANT,
    max_characters=10,
    animate_time=0.5,
    text=games[0]["AWAY"] + ' at ' + games[0]["HOME"])
    game1_text.x = 2
    game1_text.y = 5
    
    game2_text = ScrollingLabel(
    FONT,
    color=GAME_STAGNANT,
    max_characters=10,
    animate_time=0.5,
    text=games[1 % len(games)]["AWAY"] + ' at ' + games[1 % len(games)]["HOME"])
    game2_text.x = 2
    game2_text.y = 15
    
    game3_text = ScrollingLabel(
    FONT,
    color=GAME_STAGNANT,
    max_characters=10,
    animate_time=0.5,
    text=games[2 % len(games)]["AWAY"] + ' at ' + games[2 % len(games)]["HOME"])
    game3_text.x = 2
    game3_text.y = 25
        
    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(api_tilegrid)
    
    game_labels = []
    for i in range(min(len(games), 3)):  # Display up to three games
        game_text = ScrollingLabel(
            FONT,
            color=GAME_STAGNANT,
            max_characters=10,
            animate_time=0.5,
            text=games[i]["AWAY"] + ' at ' + games[i]["HOME"]
        )
        game_text.x = 2
        game_text.y = 5 + 10 * i  # Adjust the y-coordinate based on the index
        game_labels.append(game_text)
        group.append(game_text)

    rect = Rect(x=0, y=0, width=64, height=10, outline=GAME_HOVERED)
    group.append(rect)

    display.show(group)
    display.refresh()

    # ... (rest of the function remains unchanged)

    while True:
        # Wi-Fi Interrupt
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        else:
            if int(rtcobj.datetime.tm_sec) == 10:#or int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 30 or int(rtcobj.datetime.tm_sec) == 40 or int(rtcobj.datetime.tm_sec) == 50
                api_tilegrid.hidden = False
                try:
                    if state == MLB:
                        games = extract_baseball(pool)
                    elif state == NBA:
                        games = extract_basketball(pool)
                    elif state == NFL:
                        games = extract_football(pool)
                    elif state == NCAAB:
                        games = extract_ncaab(pool)
                    api_tilegrid.hidden = True
                    game1_text.text = games[game_position % len(games)]["AWAY"] + ' at ' + games[game_position % len(games)]["HOME"]
                    game2_text.text = games[(game_position + 1) % len(games)]["AWAY"] + ' at ' + games[(game_position + 1) % len(games)]["HOME"]
                    game3_text.text = games[(game_position + 2) % len(games)]["AWAY"] + ' at ' + games[(game_position + 2) % len(games)]["HOME"]
                    display.refresh()
                except:
                    print("FAIL AT GAME")
       
        if (R_button.value == False or L_button.value == False):
            game_position = (game_position + 1) % len(games)

            for i in range(min(3, len(games))):  # Update text for up to three games
                game_labels[i].text = games[(game_position + i) % len(games)]["AWAY"] + ' at ' + games[(game_position + i) % len(games)]["HOME"]

            display.refresh()
            sleep(0.2)

        # ... (rest of the loop remains unchanged)

        elif (SELECT_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            if state == MLB:
                display_MLB(display, game_position, rtcobj)
            elif state == NFL:
                display_NFL(display, game_position, rtcobj)
            elif state == NBA:
                display_NBA(display, game_position, rtcobj)
            elif state == NCAAB:
                display_NCAAB(display, game_position, rtcobj)

            sleep(0.4)
            return state

        # ... (rest of the loop remains unchanged)

        elif (BACK_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            games = []
            sleep(0.4)
            return MENU

def display_MLB(display, game_position, rtcobj):
    global games
    
    home_main = games[game_position]["HOME_COLOR_MAIN"]
    home_alt = games[game_position]["HOME_COLOR_ALT"]
    away_main = games[game_position]["AWAY_COLOR_MAIN"]
    away_alt = games[game_position]["AWAY_COLOR_ALT"]
    
    home_color, away_color = find_best_color_combo(home_main, home_alt, away_main, away_alt)
    
    away_team_text = Label(
    FONT,
    color=away_color,
    text=games[game_position]["AWAY"])
    away_team_text.x = 2
    away_team_text.y = 5
    
    at_text = Label(
    FONT,
    color=WHITE,
    text='at')
    at_text.x = 27
    at_text.y = 5
    
    home_team_text = Label(
    FONT,
    color=home_color,
    text=games[game_position]["HOME"])
    home_team_text.x = 45
    home_team_text.y = 5
    
    base_bmp = OnDiskBitmap(open("bitmaps/base.bmp", "rb"))
    base_load_bmp = OnDiskBitmap(open("bitmaps/base_loaded.bmp", "rb"))
    top_inning_bmp = OnDiskBitmap(open("bitmaps/top_inning.bmp", "rb"))
    bottom_inning_bmp = OnDiskBitmap(open("bitmaps/bottom_inning.bmp", "rb"))
 
    base1_empty_tilegrid = TileGrid(
        base_bmp,
        pixel_shader=getattr(base_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=53, #Top L
        y=14 # Top L
    )
    
    base1_filled_tilegrid = TileGrid(
        base_load_bmp,
        pixel_shader=getattr(base_load_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=53, #Top L
        y=14 # Top L
    )        
    
    base2_empty_tilegrid = TileGrid(
        base_bmp,
        pixel_shader=getattr(base_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=48, #Top L
        y=9 # Top L
    )
    
    base2_filled_tilegrid = TileGrid(
        base_load_bmp,
        pixel_shader=getattr(base_load_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=48, #Top L
        y=9 # Top L
    )
    
    base3_empty_tilegrid = TileGrid(
        base_bmp,
        pixel_shader=getattr(base_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=43, #Top L
        y=14 # Top L
    )

    base3_filled_tilegrid = TileGrid(
        base_load_bmp,
        pixel_shader=getattr(base_load_bmp, 'pixel_shader', ColorConverter()),
        tile_width=7,
        tile_height=7,
        x=43, #Top L
        y=14 # Top L
    )
    
    inning_tilegrid = TileGrid(
    top_inning_bmp,
    pixel_shader=getattr(top_inning_bmp, 'pixel_shader', ColorConverter()),
    tile_width=5,
    tile_height=8,
    x=26,
    y=27,
    )
    
    if top_or_bottom(inning_format(games[game_position]['INNING'])) is True:
        inning_tilegrid.bitmap = top_inning_bmp
    else:
        inning_tilegrid.bitmap = bottom_inning_bmp
    
    score_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['AWAY_SCORE'] + '-' + games[game_position]['HOME_SCORE']
        )
    score_text.x = 2
    score_text.y = 26
    
    inning_text = Label(
        FONT,
        color = YELLOW,
        text=inning_format(games[game_position]['INNING'])
        )
    inning_text.x = 33
    inning_text.y = 26
    
    bso_text = Label(
        FONT,
        color = YELLOW,
        text=str(games[game_position]['BALLS']) + '/' + str(games[game_position]['STRIKES']) + '/' + str(games[game_position]['OUTS'])
        )
    bso_text.x = 4
    bso_text.y = 15
    
    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(away_team_text)
    group.append(at_text)
    group.append(home_team_text)
    group.append(score_text)
    group.append(bso_text)
    group.append(api_tilegrid)
    group.append(inning_text)
    group.append(inning_tilegrid)
                    
    if games[game_position]['ON_FIRST'] is True:
        group.append(base1_filled_tilegrid)
        last_base1 = True
    else:
        group.append(base1_empty_tilegrid)
        last_base1 = False
                    
    if games[game_position]['ON_SECOND'] is True:
        group.append(base2_filled_tilegrid)
        last_base2 = True
        
    else:
        group.append(base2_empty_tilegrid)
        last_base2 = False
                    
    if games[game_position]['ON_THIRD'] is True:
        group.append(base3_filled_tilegrid)
        last_base3 = True
    else:
        group.append(base3_empty_tilegrid)
        last_base3 = False

    display.show(group)
    display.refresh()

    while True:
        # Wi-Fi Interrupt
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        else:
            # Made this less frequent because of less updates, if not responsive enough, add back 10 and 40 second interrupts
            if int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 50:
                api_tilegrid.hidden = False
                try:
                    games = extract_baseball(pool)
                    api_tilegrid.hidden = True

                    score_text=games[game_position]['AWAY_SCORE'] + '-' + games[game_position]['HOME_SCORE']
                    inning_text.text=inning_format(games[game_position]['INNING'])
                    bso_text.text=str(games[game_position]['BALLS']) + '/' + str(games[game_position]['STRIKES']) + '/' + str(games[game_position]['OUTS'])

                    
                    if games[game_position]['ON_FIRST'] is True:
                        if last_base1 is False:
                            group.remove(base1_empty_tilegrid)
                            group.append(base1_filled_tilegrid)
                            last_base1 = True
                    else:
                        if last_base1 is True:
                            group.remove(base1_filled_tilegrid)
                            group.append(base1_empty_tilegrid)
                            last_base1 = False

                                    
                    if games[game_position]['ON_SECOND'] is True:
                        if last_base2 is False:
                            group.remove(base2_empty_tilegrid)
                            group.append(base2_filled_tilegrid)
                            last_base2 = True
                            
                    else:
                        if last_base2 is True:
                            group.remove(base2_filled_tilegrid)
                            group.append(base2_empty_tilegrid)
                            last_base2 = False

                                    
                    if games[game_position]['ON_THIRD'] is True:
                        if last_base3 is False:
                            group.remove(base3_empty_tilegrid)
                            group.append(base3_filled_tilegrid)
                            last_base3 = True

                    else:
                        if last_base3 is True:
                            group.remove(base3_filled_tilegrid)
                            group.append(base3_empty_tilegrid)
                            last_base3 = False
                    
                    if top_or_bottom(inning_format(games[game_position]['INNING'])) is True:
                        inning_tilegrid.bitmap = top_inning_bmp
                    else:
                        inning_tilegrid.bitmap = bottom_inning_bmp
                    
                    display.refresh()
                except:
                    api_tilegrid.hidden = True
                    print("FAIL")

        if (BACK_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            return
        
def display_NBA(display, game_position, rtcobj):
    global games
    
    if len(games[game_position]["AWAY"]) == 3:
        away_x = 2
        away_y = 5
    else:
        away_x = 0
        away_y = 5
    
    if len(games[game_position]["HOME"]) == 3:
        home_x = 45
        home_y = 5
    else:
        home_x = 40
        home_y = 5
    
    home_main = games[game_position]["HOME_COLOR_MAIN"]
    home_alt = games[game_position]["HOME_COLOR_ALT"]
    away_main = games[game_position]["AWAY_COLOR_MAIN"]
    away_alt = games[game_position]["AWAY_COLOR_ALT"]
    
    home_color, away_color = find_best_color_combo(home_main, home_alt, away_main, away_alt)
    
    away_team_text = Label(
    FONT,
    color=away_color,
    text=games[game_position]["AWAY"])
    away_team_text.x = away_x
    away_team_text.y = away_y
    
    
    at_text = Label(
    FONT,
    color=WHITE,
    text='at')
    at_text.x = 27
    at_text.y = 5
    
    
    home_team_text = Label(
    FONT,
    color=home_color,
    text=games[game_position]["HOME"])
    home_team_text.x = home_x
    home_team_text.y = home_y
    
    
    away_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['AWAY_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(12, 10))
    
    home_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['HOME_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(53, 10))
    
    q1_bmp = OnDiskBitmap(open("bitmaps/q1.bmp", "rb"))
    q2_bmp = OnDiskBitmap(open("bitmaps/q2.bmp", "rb"))
    q3_bmp = OnDiskBitmap(open("bitmaps/q3.bmp", "rb"))
    q4_bmp = OnDiskBitmap(open("bitmaps/q4.bmp", "rb"))
    fin_bmp = OnDiskBitmap(open("bitmaps/fin.bmp", "rb"))
    
    q_tilegrid = TileGrid(
    q1_bmp,
    pixel_shader=getattr(q1_bmp, 'pixel_shader', ColorConverter()),
    tile_width=15,
    tile_height=8,
    x=24,
    y=24,
    )
    
    if games[game_position]['FINISHED'] is False:
        if games[game_position]['QUARTER'] == 1:
            q_tilegrid.bitmap = q1_bmp
        elif games[game_position]['QUARTER'] == 2:
            q_tilegrid.bitmap = q2_bmp
        elif games[game_position]['QUARTER'] == 3:
            q_tilegrid.bitmap = q3_bmp
        elif games[game_position]['QUARTER'] == 4:
            q_tilegrid.bitmap = q4_bmp
    else:
        q_tilegrid.bitmap = fin_bmp
    
    basketball_bmp = OnDiskBitmap(open("bitmaps/basketball.bmp", "rb"))
    basketball_tilegrid = TileGrid(
    basketball_bmp,
    pixel_shader=getattr(basketball_bmp, 'pixel_shader', ColorConverter()),
    tile_width=11,
    tile_height=11,
    x=26,
    y=12,
    )
    
    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(api_tilegrid)
    group.append(away_team_text)
    group.append(at_text)
    group.append(home_team_text)
    group.append(q_tilegrid)
    group.append(away_text)
    group.append(home_text)
    group.append(basketball_tilegrid)
    display.show(group)
    display.refresh()

    while True:
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        else:
            if int(rtcobj.datetime.tm_sec) == 10 or int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 40 or int(rtcobj.datetime.tm_sec) == 50:
                api_tilegrid.hidden = False
                try:
                    games = extract_basketball(pool)
                    api_tilegrid.hidden = True
                    away_team_text.text=games[game_position]["AWAY"]
                    at_text.text='at'
                    home_team_text.text=games[game_position]["HOME"]
                    away_text.text=games[game_position]['AWAY_SCORE']
                    home_text.text=games[game_position]['HOME_SCORE']
                    
                    
                    if games[game_position]['FINISHED'] is False:
                        if games[game_position]['QUARTER'] == 1:
                            q_tilegrid.bitmap = q1_bmp
                        elif games[game_position]['QUARTER'] == 2:
                            q_tilegrid.bitmap = q2_bmp
                        elif games[game_position]['QUARTER'] == 3:
                            q_tilegrid.bitmap = q3_bmp
                        elif games[game_position]['QUARTER'] == 4:
                            q_tilegrid.bitmap = q4_bmp
                    else:
                        q_tilegrid.bitmap = fin_bmp
                    
                    
                    display.refresh()
                except:
                    print("FAIL")
                    
                api_tilegrid.hidden = True

        if (BACK_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            return
        
def display_NCAAB(display, game_position, rtcobj):
    global games
    
    if len(games[game_position]["AWAY"]) == 3:
        away_x = 2
        away_y = 5
    else:
        away_x = 0
        away_y = 5
    
    if len(games[game_position]["HOME"]) == 3:
        home_x = 45
        home_y = 5
    else:
        home_x = 40
        home_y = 5
    
    home_main = games[game_position]["HOME_COLOR_MAIN"]
    home_alt = games[game_position]["HOME_COLOR_ALT"]
    away_main = games[game_position]["AWAY_COLOR_MAIN"]
    away_alt = games[game_position]["AWAY_COLOR_ALT"]
    
    home_color, away_color = find_best_color_combo(home_main, home_alt, away_main, away_alt)
    
    away_team_text = Label(
    FONT,
    color=away_color,
    text=games[game_position]["AWAY"])
    away_team_text.x = away_x
    away_team_text.y = away_y
    
    
    at_text = Label(
    FONT,
    color=WHITE,
    text='at')
    at_text.x = 27
    at_text.y = 5
    
    
    home_team_text = Label(
    FONT,
    color=home_color,
    text=games[game_position]["HOME"])
    home_team_text.x = home_x
    home_team_text.y = home_y
    
    
    away_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['AWAY_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(12, 10))
    
    home_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['HOME_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(53, 10))
    
    q1_bmp = OnDiskBitmap(open("bitmaps/q1.bmp", "rb"))
    q2_bmp = OnDiskBitmap(open("bitmaps/q2.bmp", "rb"))
    q3_bmp = OnDiskBitmap(open("bitmaps/q3.bmp", "rb"))
    q4_bmp = OnDiskBitmap(open("bitmaps/q4.bmp", "rb"))
    fin_bmp = OnDiskBitmap(open("bitmaps/fin.bmp", "rb"))
    
    q_tilegrid = TileGrid(
    q1_bmp,
    pixel_shader=getattr(q1_bmp, 'pixel_shader', ColorConverter()),
    tile_width=15,
    tile_height=8,
    x=24,
    y=24,
    )
    
    if games[game_position]['FINISHED'] is False:
        if games[game_position]['QUARTER'] == 1:
            q_tilegrid.bitmap = q1_bmp
        elif games[game_position]['QUARTER'] == 2:
            q_tilegrid.bitmap = q2_bmp
        elif games[game_position]['QUARTER'] == 3:
            q_tilegrid.bitmap = q3_bmp
        elif games[game_position]['QUARTER'] == 4:
            q_tilegrid.bitmap = q4_bmp
    else:
        q_tilegrid.bitmap = fin_bmp
    
    basketball_bmp = OnDiskBitmap(open("bitmaps/basketball.bmp", "rb"))
    basketball_tilegrid = TileGrid(
    basketball_bmp,
    pixel_shader=getattr(basketball_bmp, 'pixel_shader', ColorConverter()),
    tile_width=11,
    tile_height=11,
    x=26,
    y=12,
    )
    
    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(api_tilegrid)
    group.append(away_team_text)
    group.append(at_text)
    group.append(home_team_text)
    group.append(q_tilegrid)
    group.append(away_text)
    group.append(home_text)
    group.append(basketball_tilegrid)
    display.show(group)
    display.refresh()

    while True:
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        else:
            if int(rtcobj.datetime.tm_sec) == 10 or int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 40 or int(rtcobj.datetime.tm_sec) == 50:
                api_tilegrid.hidden = False
                try:
                    games = extract_NCAAB(pool)
                    api_tilegrid.hidden = True
                    away_team_text.text=games[game_position]["AWAY"]
                    at_text.text='at'
                    home_team_text.text=games[game_position]["HOME"]
                    away_text.text=games[game_position]['AWAY_SCORE']
                    home_text.text=games[game_position]['HOME_SCORE']
                    
                    
                    if games[game_position]['FINISHED'] is False:
                        if games[game_position]['QUARTER'] == 1:
                            q_tilegrid.bitmap = q1_bmp
                        elif games[game_position]['QUARTER'] == 2:
                            q_tilegrid.bitmap = q2_bmp
                        elif games[game_position]['QUARTER'] == 3:
                            q_tilegrid.bitmap = q3_bmp
                        elif games[game_position]['QUARTER'] == 4:
                            q_tilegrid.bitmap = q4_bmp
                    else:
                        q_tilegrid.bitmap = fin_bmp
                    
                    
                    display.refresh()
                except:
                    print("FAIL")
                    
                api_tilegrid.hidden = True

        if (BACK_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            return

def display_NFL(display, game_position, rtcobj):
    global games
    home_main = games[game_position]["HOME_COLOR_MAIN"]
    home_alt = games[game_position]["HOME_COLOR_ALT"]
    away_main = games[game_position]["AWAY_COLOR_MAIN"]
    away_alt = games[game_position]["AWAY_COLOR_ALT"]
    
    home_color, away_color = find_best_color_combo(home_main, home_alt, away_main, away_alt)
    
    away_team_text = Label(
    FONT,
    color=away_color,
    text=games[game_position]["AWAY"])
    away_team_text.x = 2
    away_team_text.y = 5
    
    
    at_text = Label(
    FONT,
    color=WHITE,
    text='at')
    at_text.x = 27
    at_text.y = 5
    
    
    home_team_text = Label(
    FONT,
    color=home_color,
    text=games[game_position]["HOME"])
    home_team_text.x = 45
    home_team_text.y = 5
    
    away_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['AWAY_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(12, 15))
    
    home_text = Label(
        FONT,
        color = WHITE,
        text=games[game_position]['HOME_SCORE'],
        anchor_point=(0.5,0),
        anchored_position=(53, 15))
    
    q1_bmp = OnDiskBitmap(open("bitmaps/q1.bmp", "rb"))
    q2_bmp = OnDiskBitmap(open("bitmaps/q2.bmp", "rb"))
    q3_bmp = OnDiskBitmap(open("bitmaps/q3.bmp", "rb"))
    q4_bmp = OnDiskBitmap(open("bitmaps/q4.bmp", "rb"))
    fin_bmp = OnDiskBitmap(open("bitmaps/fin.bmp", "rb"))

    
    q_tilegrid = TileGrid(
    q1_bmp,
    pixel_shader=getattr(q1_bmp, 'pixel_shader', ColorConverter()),
    tile_width=15,
    tile_height=8,
    x=24,
    y=24,
    )
    
    if games[game_position]['FINISHED'] is False:
        if games[game_position]['QUARTER'] == 1:
            q_tilegrid.bitmap = q1_bmp
        elif games[game_position]['QUARTER'] == 2:
            q_tilegrid.bitmap = q2_bmp
        elif games[game_position]['QUARTER'] == 3:
            q_tilegrid.bitmap = q3_bmp
        elif games[game_position]['QUARTER'] == 4:
            q_tilegrid.bitmap = q4_bmp
    else:
        q_tilegrid.bitmap = fin_bmp
        
    fball_bmp = OnDiskBitmap(open("bitmaps/fball.bmp", "rb"))
    fball_tilegrid = TileGrid(
    fball_bmp,
    pixel_shader=getattr(fball_bmp, 'pixel_shader', ColorConverter()),
    tile_width=11,
    tile_height=7,
    x=26,
    y=16,
    )
    
    
    group = Group()
    group.append(wifi_small_tilegrid)
    group.append(api_tilegrid)
    group.append(away_team_text)
    group.append(home_team_text)
    group.append(at_text)
    group.append(away_text)
    group.append(home_text)
    group.append(fball_tilegrid)
    group.append(q_tilegrid)
    display.show(group)
    display.refresh()

    while True:
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                if int(rtcobj.datetime.tm_sec) == 30:
                    init_WIFI(ssid, password)
                    wifi_small_tilegrid.hidden = True
            except:
                pass
        else:
            if int(rtcobj.datetime.tm_sec) == 10 or int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 40 or int(rtcobj.datetime.tm_sec) == 50:
                api_tilegrid.hidden = False
                try:
                    games = extract_football(pool)
                    api_tilegrid.hidden = True
                    away_team_text.text=games[game_position]["AWAY"]
                    at_text.text='at'
                    home_team_text.text=games[game_position]["HOME"]
                    away_text.text=games[game_position]['AWAY_SCORE']
                    home_text.text=games[game_position]['HOME_SCORE']
                    9
                    if games[game_position]['FINISHED'] is False:
                        if games[game_position]['QUARTER'] == 1:
                            q_tilegrid.bitmap = q1_bmp
                        elif games[game_position]['QUARTER'] == 2:
                            q_tilegrid.bitmap = q2_bmp
                        elif games[game_position]['QUARTER'] == 3:
                            q_tilegrid.bitmap = q3_bmp
                        elif games[game_position]['QUARTER'] == 4:
                            q_tilegrid.bitmap = q4_bmp
                    else:
                        q_tilegrid.bitmap = fin_bmp
                    
                    display.refresh()
                except:
                    print("FAIL")
                
                api_tilegrid.hidden = True
        
        # Wi-Fi Interrupt
        if radio.connected == False:
            wifi_small_tilegrid.hidden = False
            try:
                init_WIFI(ssid, password)
                wifi_small_tilegrid.hidden = True
            except:
                pass


        if (BACK_button.value == False):
            group.remove(wifi_small_tilegrid)
            group.remove(api_tilegrid)
            return

async def update_CLOCK(rtcobj, time_text):
    await asyncio.sleep(1)
    hour = None
    ampm = None
    if int(rtcobj.datetime.tm_hour) > 12:
        hour = int(rtcobj.datetime.tm_hour) - 12
        ampm = 'PM' 
    else:
        hour = int(rtcobj.datetime.tm_hour)
        ampm = 'AM'
    time_text.text = f'{hour:02}' + ':' + f'{int(rtcobj.datetime.tm_min):02}'
    
    if radio.connected == False:
        wifi_small_tilegrid.hidden = False
    
    if int(rtcobj.datetime.tm_sec) == 10 or int(rtcobj.datetime.tm_sec) == 20 or int(rtcobj.datetime.tm_sec) == 30 or int(rtcobj.datetime.tm_sec) == 40 or int(rtcobj.datetime.tm_sec) == 50:
        await wifi_reconnect()
    

async def display_CLOCK(display, rtcobj):
    global clock_color
    print('Outside', clock_color)
    hour = None
    ampm = None
    if int(rtcobj.datetime.tm_hour) > 12:
        hour = int(rtcobj.datetime.tm_hour) - 12
        ampm = 'PM'
    elif int(rtcobj.datetime.tm_hour) == 12:
        ampm = 'PM'
    else:
        hour = int(rtcobj.datetime.tm_hour)
        ampm = 'AM'
    #response = update_CLOCK(requests)
    time_text = Label(
    FONT,
    color=clock_color,
    text=f'{hour:02}' + ':' + f'{int(rtcobj.datetime.tm_min):02}',
    scale=2)
    time_text.x = 3
    time_text.y = 11
    
    am_pm_text = Label(
    FONT,
    color=clock_color,
    text=ampm,
    scale=1)
    am_pm_text.x = 27
    am_pm_text.y = 26
    
    group = Group()
    group.append(time_text)
    group.append(am_pm_text)
    group.append(wifi_small_tilegrid)
    display.show(group)
    display.refresh()
    
    while True:
        clock_task = asyncio.create_task(update_CLOCK(rtcobj, time_text))
        await asyncio.gather(clock_task)
        
        #if L_button.value == False or R_button.value == False:        
        if BACK_button.value == False or SELECT_button.value == False:
            if clock_color == GREEN:
                clock_color = WHITE
            elif clock_color == WHITE:
                clock_color = BLUE
            elif clock_color == BLUE:
                clock_color = RED
            elif clock_color == RED:
                clock_color = YELLOW
            elif clock_color == YELLOW:
                clock_color = CYAN
            elif clock_color == CYAN:
                clock_color = GREEN
            else:
                clock_color = GREEN
            group.remove(wifi_small_tilegrid)
            return MENU


async def wifi_reconnect():
    if radio.connected == False:
        print("Wi-Fi Disconnected, reconnecting...")
        try:
            init_WIFI(ssid, password)
            wifi_small_tilegrid.hidden = True
        except:
            pass

if __name__ == "__main__":
    
    # Initialize Display
    collect()
    display = init_Display()
    #ssid, password = find_WIFI()
    rtcobj = init_WIFI('SpectrumSetup-3D', 'YourMomIsBoss')

    remount("/", False)
    
    sleep(2)
    state = MENU
    
    while True:
        if state == MENU:
            state = display_Menu(display)
        elif state == NFL or state == NBA or state == MLB or state == NCAAB:
            state = display_GAMES(display, rtcobj)
        elif state == CLOCK:
            if radio.connected:
                state = asyncio.run(display_CLOCK(display, rtcobj))
            else:
                state = MENU
            
    remount("/", True)
    

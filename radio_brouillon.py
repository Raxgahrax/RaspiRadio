#!/usr/bin/python

# radio.py, version 2.1 (RGB LCD Pi Plate version)
# February 17, 2013
# Edited by Raxgahrax (2016/2017)
# Written by Sheldon Hartling for Usual Panic
# BSD license, all text above must be included in any redistribution
#

#
# based on code from Kyle Prier (http://wwww.youtube.com/meistervision)
# and AdaFruit Industries (https://www.adafruit.com)
# Kyle Prier - https://www.dropbox.com/s/w2y8xx7t6gkq8yz/radio.py
# AdaFruit   - https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code.git, Adafruit_CharLCDPlate
#

#dependancies
import time
import RPi.GPIO as GPIO
import Adafruit_CharLCD as LCD
import Adafruit_GPIO.MCP230xx as MCP

from time                  import sleep, strftime
from Queue                 import Queue
from smbus                 import SMBus
from datetime              import datetime
from threading             import Thread
from subprocess            import *


# Define MCP pins connected to the LCD.
lcd_rs        = 0
lcd_en        = 1
lcd_d4        = 2
lcd_d5        = 3
lcd_d6        = 4
lcd_d7        = 5
lcd_red       = 6
lcd_green     = 7
lcd_blue      = 8

# Define LCD column and row size for 16x2 LCD.
lcd_columns = 16
lcd_rows = 2

# Initialize MCP23017 device using its default 0x20 I2C address.
gpio = MCP.MCP23017()

# Initialize the LCD using the pins
lcd = LCD.Adafruit_RGBCharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, 
                              lcd_rows, lcd_red, lcd_green, lcd_blue, gpio=gpio)

# Define a queue to communicate with worker thread
LCD_QUEUE = Queue()

# Globals
PLAYLIST_MSG   = []
STATION        = 1
NUM_STATIONS   = 0

# ----------------------------
# WORKER THREAD
# ----------------------------

# Define a function to run in the worker thread
def update_lcd(q):
   
   while True:
      msg = q.get()
      # if we're falling behind, skip some LCD updates
      while not q.empty():
         q.task_done()
         msg = q.get()
      LCD.setCursor(0,0)
      LCD.message(msg)
      q.task_done()
   return

# ----------------------------
# MAIN LOOP
# ----------------------------

def main():
   global STATION, NUM_STATIONS, PLAYLIST_MSG

   # Stop music player
   output = run_cmd("mpc stop")

   # Setup AdaFruit LCD Plate
   lcd.clear()
   lcd.set_color(1.0, 0.0, 1.0)

   # Create the worker thread and make it a daemon
   worker = Thread(target=update_lcd, args=(LCD_QUEUE,))
   worker.setDaemon(True)
   worker.start()
   
   # Display startup banner
   LCD_QUEUE.put('Welcome to\nRaspiPanic Radio', True)

   # Load our station playlist
   load_playlist()
   sleep(2)
   lcd.clear()

# ----------------------------
# START THE MUSIC!
# ----------------------------

   # Start music player
   LCD_QUEUE.put(PLAYLIST_MSG[STATION - 1], True)
   run_cmd("mpc volume +100")
   mpc_play(STATION)
   countdown_to_play = 0
      
   # Main loop
   while True:
      press = read_buttons()

      # LEFT button pressed
      if(press == LEFT):
         STATION -= 1
         if(STATION < 1):
            STATION = NUM_STATIONS
         LCD_QUEUE.put(PLAYLIST_MSG[STATION - 1], True)
         # start play in 300msec unless another key pressed
         countdown_to_play = 3

      # RIGHT button pressed
      if(press == RIGHT):
         STATION += 1
         if(STATION > NUM_STATIONS):
            STATION = 1
         LCD_QUEUE.put(PLAYLIST_MSG[STATION - 1], True)
         # start play in 300msec unless another key pressed
         countdown_to_play = 3

      # UP button pressed
      if(press == UP):
         output = run_cmd("mpc volume +2")

      # DOWN button pressed
      if(press == DOWN):
         output = run_cmd("mpc volume -2")

      # SELECT button pressed
      if(press == SELECT):
         menu_pressed()

      # If we haven't had a key press in 300 msec
      # go ahead and issue the MPC command
      if(countdown_to_play > 0):
         countdown_to_play -= 1
         if(countdown_to_play == 0):
            # Play requested station
            mpc_play(STATION)

      delay_milliseconds(99)
   update_lcd.join()

# ----------------------------
# READ SWITCHES
# ----------------------------

def read_buttons():

   buttons = LCD.readButtons()
   # Debounce push buttons
   if(buttons != 0):
      while(LCD.readButtons() != 0):
         delay_milliseconds(1)
   return buttons



def delay_milliseconds(milliseconds):
   seconds = milliseconds / float(1000)	# divide milliseconds by 1000 for seconds
   sleep(seconds)

# ----------------------------
# LOAD PLAYLIST OF STATIONS
# ----------------------------

def load_playlist():
   global STATION, NUM_STATIONS, PLAYLIST_MSG

   # Run shell script to add all stations
   # to the MPC/MPD music player playlist
   output = run_cmd("mpc clear")
   output = run_cmd("/home/pi/Desktop/RaspiRadio/playlist.sh")

   # Load PLAYLIST_MSG list
   PLAYLIST_MSG = []
   with open ("/home/pi/Desktop/RaspiRadio/playlist.sh", "r") as playlist:
      # Skip leading hash-bang line
      for line in playlist:
         if line[0:1] != '#!':  
               break
      # Remaining comment lines are loaded
      for line in playlist:
         if line[0] == "#" :
            PLAYLIST_MSG.append(line.replace(r'\n','\n')[1:-1] + "                ")
   playlist.close()
   NUM_STATIONS = len(PLAYLIST_MSG)

# ----------------------------
# RADIO SETUP MENU
# ----------------------------

def menu_pressed():
   global STATION

   MENU_LIST = [
      '1. Horloge\n & Adresse IP',
      '2. Output Audio\n To HDMI',
      '3. Output Audio\n To Headphones',
      '4. Auto Select\n Audio Output',
      '5. Rechargement\n Playlist Radio',
      '6. Extinction du\n Systeme !',
      '7. Sortie\n']

   item = 0
   lcd.clear()
   lcd.set_color(1.0, 1.0, 0.0)
   LCD_QUEUE.put(MENU_LIST[item], True)

   keep_looping = True
   while (keep_looping):

      # Wait for a key press
      press = read_buttons()

      # UP button
      if(press == UP):
         item -= 1
         if(item < 0):
            item = len(MENU_LIST) - 1
         LCD_QUEUE.put(MENU_LIST[item], True)

      # DOWN button
      elif(press == DOWN):
         item += 1
         if(item >= len(MENU_LIST)):
            item = 0
         LCD_QUEUE.put(MENU_LIST[item], True)

      # SELECT button = exit
      elif(press == SELECT):
         keep_looping = False

         # Take action
         if(  item == 0):
            # 1. display time and IP address
            display_ipaddr()
         elif(item == 1):
            # 2. audio output to HDMI
            output = run_cmd("amixer -q cset numid=3 2")
         elif(item == 2):
            # 3. audio output to headphone jack
            output = run_cmd("amixer -q cset numid=3 1")
         elif(item == 3):
            # 4. audio output auto-select
            output = run_cmd("amixer -q cset numid=3 0")
         elif(item == 4):
            # 5. reload our station playlist
            LCD_QUEUE.put(" Rechargement\n Playlist Radio..", True)
            load_playlist()
            sleep(2)
            STATION = 1
            LCD_QUEUE.put(PLAYLIST_MSG[STATION - 1], True)
            mpc_play(STATION)
         elif(item == 5):
            # 6. shutdown the system
            LCD_QUEUE.put(' Extinction de/n votre Linux !', True)
            LCD_QUEUE.join()
            output = run_cmd("mpc clear")
            output = run_cmd("sudo shutdown -h now")
            lcd.clear()
            lcd.set_color(0.0, 0.0, 0.0)
            exit(0)
      else:
         delay_milliseconds(99)

   # Restore display
   lcd.set_color(1.0, 0.0, 1.0)
   LCD_QUEUE.put(PLAYLIST_MSG[STATION - 1], True)



# ----------------------------
# DISPLAY TIME AND IP ADDRESS
# ----------------------------

def display_ipaddr():
   show_wlan0 = "ip addr show wlan0 | cut -d/ -f1 | awk '/inet/ {printf \"w%15.15s\", $2}'"
   show_eth0  = "ip addr show eth0  | cut -d/ -f1 | awk '/inet/ {printf \"e%15.15s\", $2}'"
   ipaddr = run_cmd(show_eth0)
   if ipaddr == "":
      ipaddr = run_cmd(show_wlan0)
#Bleu azur profond
   lcd.set_color(0.0, 0.0, 1.0)
   i = 29
   muting = False
   keep_looping = True
   while (keep_looping):

      # Every 1/2 second, update the time display
      i += 1
      #if(i % 10 == 0):
      if(i % 5 == 0):
#	     LCD_QUEUE.put(datetime.now().strftime('%d/%m/%y %H:%M:%S\n')+ ipaddr, True)
         LCD_QUEUE.put(datetime.now().strftime('%d %b %H:%M:%S\n')+ ipaddr, True)
		 
      # Every 3 seconds, update ethernet or wi-fi IP address
      if(i == 60):
         ipaddr = run_cmd(show_eth0)
         i = 0
      elif(i == 30):
         ipaddr = run_cmd(show_wlan0)

      # Every 100 milliseconds, read the switches
      press = read_buttons()
      # Take action on switch press
      
      # UP button pressed
      if(press == UP):
         output = run_cmd("mpc volume +2")

      # DOWN button pressed
      if(press == DOWN):
         output = run_cmd("mpc volume -2")

      # SELECT button = exit
      if(press == SELECT):
         keep_looping = False

      # LEFT or RIGHT toggles mute
      elif(press == LEFT or press == RIGHT ):
         if muting:
            #amixer command not working, can't use next line
            #output = run_cmd("amixer -q cset numid=2 1")
            mpc_play(STATION)
            # work around a problem.  Play always starts at full volume
            delay_milliseconds(400)
            output = run_cmd("mpc volume +2")
            output = run_cmd("mpc volume -2")
         else:
            #amixer command not working, can't use next line
            #output = run_cmd("amixer -q cset numid=2 0")
            output = run_cmd("mpc stop" )
         muting = not muting
         
      delay_milliseconds(99)



# ----------------------------

def run_cmd(cmd):
   p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
   output = p.communicate()[0]
   return output



#def run_cmd_nowait(cmd):
#   pid = Popen(cmd, shell=True, stdout=NONE, stderr=STDOUT).pid



def mpc_play(STATION):
   pid = Popen(["/usr/bin/mpc", "play", '%d' % ( STATION )]).pid



if __name__ == '__main__':
  main()
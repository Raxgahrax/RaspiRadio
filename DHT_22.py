#!/usr/bin/python
# coding: utf-8

import sys
import time
import Adafruit_DHT
from Adafruit_BME280 import *

#DHT22
humidity, temperature = Adafruit_DHT.read_retry(22, 4)
print('Temp      = {0:0.1f} *C'.format(temperature))  
print('Humidity  = {0:0.1f} %'.format(humidity))
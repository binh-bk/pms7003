#! /usr/bin/python3
# Binh Nguyen, April 06, 2019
import time
from pms7003 import Plantower

# create an instance with active mode
pms1 = Plantower(name='P11', port='/dev/ttyUSB0', debug=True, mode='passive', is_data_logged=True, logFile='PMS7003_P11.csv')
# create an instance with passive mode
pms2 = Plantower(name='P12', port='/dev/ttyUSB1', debug=True, mode='passive', is_data_logged=True, logFile='PMS7003_P12.csv')
# pms3 = Plantower(name='A1', port='/dev/ttyUSB0', debug=False, mode='active', is_data_logged=True, logFile='PMS7003_A1.csv')
while True:
    # if pms3.sampling(30):
    # # '''read data for every 30 seconds'''
    #     pms3.start()
    #     pms3.lastSample = time.time()
    if pms1.sampling(30):
        '''30 second sleeping (fan off) between each cycle'''
        pms1.start()
        pms1.lastTurnOn = time.time()
    if pms1.warmUp(20):
        '''turn fan on for 20 secconds, take a reading, >>> total cycle 50 seconds'''
        if pms1.readPassive():
            pms1.lastSample = time.time()

    if pms2.sampling(10):
        '''10 second sleeping (fan off) between each cycle'''
        pms2.start()
        pms2.lastTurnOn = time.time()
    if pms2.warmUp(20):
        '''turn fan on for 20 secconds, take a reading, >>> total cycle 30 seconds'''
        if pms2.readPassive():
            pms2.lastSample = time.time()
    else:
        time.sleep(1)
# PMS7003 PMS5003 Plantower PM2.5 dust sensor
## How to use:
1. Install pyserial if you have not done so `pip3 install pyserial`
2. Edit examples.py, select `port`, a `mode='passive'` or `mode='active'` and named a `logFile` for saving data
3. Make sure designate the right USB port to the sensor, on Linux check it(them) by `ls /dev/ttyUSB*`
4. If running on `mode='active'`, only interval of logging data is needed. For example, `pms3.sampling(30)` indcates a 30 seconds between data readding
5. If running on `mode='passive'`, specifying duration of sleeping (fan is off) in `pms1.sampling(60)`, 50 (seconds) for sleeping in this case, and the "warm up" time (fan on to purge the old air) such as `pms1.warmUp(30)` for 30 seconds of warm-up. 30 seconds are sufficient according to the Plantower datasheet.
## Demo Video:
[![Youtube Demo](http://img.youtube.com/vi/9dTJ1QQIeTA/0.jpg)](http://www.youtube.com/watch?v=9dTJ1QQIeTA "Python Interface for Plantower x003")
## Credits:
the class is built from this project (https://pypi.org/project/plantower/). Credits to Philip Basford

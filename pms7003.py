"""
	Wrapper classes for the PMS7003, PMS5003
	Binh Nguyen, Jan20, 2019, 
	forked from Philip Basford Plantower PMS5003.
"""

import time, os, struct
from serial import Serial, SerialException

def time_(): return int(time.time())

def host_folder():
	"""designate a folder to save each month"""

	this_month_folder = time.strftime('%Y%b')
	basedir = os.path.abspath(os.path.dirname(__file__))
	all_dirs = [d for d in os.listdir(basedir) if os.path.isdir(d)]
	if len(all_dirs) == 0 or this_month_folder not in all_dirs:
		os.makedirs(this_month_folder)
		print('created: {}'.format(this_month_folder))
	return os.path.join(basedir, this_month_folder)

class PlantowerReading(object):
	"""Data extraction for PMS7003 sensor"""
	
	def __init__(self, line):
		"""
			Takes a line from the Plantower serial port and converts it into
			an object containing the data
		"""
		self.timestamp = time.strftime('%x %X', time.localtime())
		self.pm10_cf1 = line[4] * 256 + line[5]
		self.pm25_cf1 = line[6] * 256 + line[7]
		self.pm100_cf1 = line[8] * 256 + line[9]
		self.pm10_std = line[10] * 256 + line[11]
		self.pm25_std = line[12] * 256 + line[13]
		self.pm100_std = line[14] * 256 + line[15]
		self.gr03um = line[16] * 256 + line[17]
		self.gr05um = line[18] * 256 + line[19]
		self.gr10um = line[20] * 256 + line[21]
		self.gr25um = line[22] * 256 + line[23]
		self.gr50um = line[24] * 256 + line[25]
		self.gr100um = line[26] * 256 + line[27]
	
	def pm25_es(self):
		"""estimate PM2.5 concentration based particle counts"""
		import math
		count = self.gr03um - self.gr25um
		# https://github.com/andy-pi/weather-monitor/blob/master/air_quality.py
		# assume density of particle 1.65E12 ug/m3
		d_pm25 = 1.65*math.pow(10, 12)
		# assume the average particle in chanel PM2.5 is 0.44 um
		r_pm25 = 0.44*math.pow(10, -6)
		v_pm25 = (4/3)*math.pi*(r_pm25**3)
		mass_pm25 = v_pm25*d_pm25
		# concentration in 0.1L air, convert to ug/m
		return round(mass_pm25*10*(1000)*count,1)

	def __str__(self):
		return (f"{self.timestamp},{self.pm10_cf1},{self.pm25_cf1},{self.pm100_cf1},{self.pm10_std},{self.pm25_std},{self.pm100_std},{self.gr03um},{self.gr05um},{self.gr10um},{self.gr25um},{self.gr50um},{self.gr100um},{self.pm25_es()}")

class Plantower(object):
	"""Actual interface to the PMS7003 sensor"""
	# class attributes
	name = "PMS7003"
	baud = 9600
	mode = "active"
	debug = False
	is_data_logged = True
	logFile='PMS7003.csv'
	lastSample = 0
	lastTurnOn = 0
	max_try = 0
	custom_msg = f'data captured Python Script directly from {name} >> USB >>PC\n'

	def __init__(self, name, port, mode, debug, logFile, is_data_logged):
		"""Setup the interface for the sensor"""

		self.name = name
		self.port = port
		self.mode = mode
		self.debug = debug
		self.logFile = logFile
		self.is_data_logged = is_data_logged
  
		try:
			self.serial = Serial(
				port=self.port, baudrate=self.baud,
				timeout=1)
		except SerialException as exp:
			print(f'Time {time_}: {exp}')

	@staticmethod
	def build_cmd(mode):
		'''
		construct a custom command and sent to the serial port
		https://github.com/teusH/MySense/blob/master/PyCom/lib/PMSx003.py
		send 42 4D cmd(E2, E4, E1) 00 ON(On=1, Off=0) chckH chckL
		no answer on cmd: E2 (read telegram) and E4 On (active mode)
		answer 42 4D 00 04 cmd 00 chckH chckL
		'''
		d = [0x42,0x4D]
		if mode == 'sleep':
			cmd = [0xE4, 0x00, 0x00]
		elif mode == 'wakeup':
			cmd = [0xE4, 0x00, 0x01]
		elif mode == 'active':
			cmd = [0xE1, 0x00, 0x01]
		elif mode == 'passive':
			cmd = [0XE1, 0x00, 0x00]
		elif mode == 'read_passive':
			cmd = [0xE2, 0x00, 0x00]
		else:
			print('No mode selected')
			return 
		d += cmd
		ckcSum = sum(x for x in d)
		d += [ckcSum]
		cmd = struct.pack('!BBBBBH', d[0], d[1], d[2], d[3], d[4], d[5])
		return cmd
	
	@staticmethod
	def p_print(binary_string):
		'''return a easy to read heximal string'''
		return ' '.join([f'{x:02X}' for x in binary_string.strip()])

	def send_cmd(self, cmd):
		'''send command to the sensor'''
		try:
			self.serial.reset_output_buffer()
			time.sleep(0.1)
			self.serial.write(cmd)
			self.serial.flush()
			if self.debug:
				print(f'{self.name }> {self.p_print(cmd)}')
		except Exception as e:
			print(f'Exp as {e}')
		return None

	def wakeUp(self):
		'''walking up sensor in passive mode'''
		cmd = self.build_cmd('wakeup')
		self.send_cmd(cmd)
		return 

	def sleep(self):
		'''put sensor into sleep in passive mode'''
		cmd = self.build_cmd('sleep')
		# print(f'Sleep...')
		self.send_cmd(cmd)
		return None

	def _verify(self, recv):
		"""
			Uses the last 2 bytes of the data packet from the Plantower sensor
			to verify that the data recived is correct
		"""
		calc = 0
		ord_arr = []
		for c in bytearray(recv[:-2]): #Add all the bytes together except the checksum bytes
			calc += c
			ord_arr.append(c)
		sent = (recv[-2] << 8) | recv[-1] # Combine the 2 bytes together
		if sent != calc:
			print('Unmached CHECKSUM')
			return -1
		return True

	def read(self, perform_flush=True):
		"""
			Reads a line from the serial port and return
			if perform_flush is set to true it will flush the serial buffer
			before performing the read, otherwise, it'll just read the first
			item in the buffer
		"""
		recv = b''
		start = time.time() #Start timer
		try:
			if perform_flush:
				# print(f'Buffer before reset {self.serial.in_waiting}')
				self.serial.reset_input_buffer() #Flush any data in the buffer
				self.serial.reset_output_buffer()
			while self.serial.in_waiting <32:
				time.sleep(0.7)
				self.max_try +=1
				if self.debug: print(f'{self.name} with try # {self.max_try}')
				if self.max_try >=5:
					self.max_try = 0
				break
		   
			while(time.time() < (start + 1)): # allow 1 second for reading
				inp = self.serial.read() # Read a character from the input
				if inp == b'\x42': # check it matches
					recv += inp # if it does add it to recieve string
					inp = self.serial.read() # read the next character
					if inp == b'\x4d': # check it's what's expected
						recv += inp # att it to the recieve string
						recv += self.serial.read(30) # read the remaining 30 bytes
						if self._verify(recv): # verify the 
							# print(f'< {recv}')
							if self.debug: print(f"Receive < {self.p_print(recv)}")
							return PlantowerReading(recv) # convert to reading object
						else:
							time.sleep(0.7)
							print('CKC failed, continue...')
							continue         
				continue
		except Exception as e:
			print(f'Error as {e}')
		return -1

	def data_record(self,output):
		'''record data into a csv file with the custom header'''

		if self.is_data_logged:
			logFile = self.logFile
			logFile = os.path.join(host_folder(), logFile)
			if self.debug: print(f'Log file {logFile}')
			with open(logFile, 'a+') as f:
				if self.lastSample == 0:
					'''initial setup'''
					f.seek(0)
					head_ = f.readline().lower()
					if not head_.startswith("data captured"):
						print(f'Head as {head_}')
						print(f'LogFile as {logFile}')
						headers = '''time,pm1.0_cf,pm2.5_cf,pm10_cf,pm1.0_ac,pm2.5_ac,pm10_ac,um03,um05,um1,um2.5,um5.0,um10,pm2.5_es\n'''
						f.write(self.custom_msg)
						f.write(headers)
						
					else:
						'''log data to an existing file'''
						time_ = time.strftime('%x %X', time.localtime())
						sprtor = '{},0,0,0,0,0,0,0,0,0,0,0,0\n'.format(time_)
						f.write(sprtor)
				else:
					try:
						len_ = len(output.split(','))
						if len_ > 1:
							output += '\n'
							f.write(output)
						return None
					except Exception as e:
						print('Error! {}'.format(e))
						return -1

	def readPassive(self):
		'''reading data in the passive mode'''

		cmd = self.build_cmd('read_passive')
		self.send_cmd(cmd)
		output = self.read().__str__()
		try:
			len_ = len(output.split(','))
			if len_ >1:
				if self.is_data_logged:
					self.data_record(output)
				print(f'{self.name}:>> {output}')
				print('-'*30)
				self.sleep()
				print(f'{self.name} sleeping...')
				return True
		except Exception as e:
			print(f'Error as reading {e}')
			return False

	def start(self):
		'''
		start sensor in both mode, and read from sensor in passive mode
		'''
		if self.mode == 'active':
			if self.lastSample == 0:
				'''only run one after starting up'''
				cmd = self.build_cmd('active')
				self.send_cmd(cmd)
				time.sleep(0.1)
				self.wakeUp()
			output = self.read().__str__()
			if self.is_data_logged:
				self.data_record(output)
			print(f'{self.name}:>> {output}')
			print('-'*30)
		elif self.mode == 'passive':
			if self.lastSample == 0:
				cmd = self.build_cmd('passive')
				self.send_cmd(cmd)
				time.sleep(0.1)
				if self.is_data_logged:
					self.data_record(None)
				self.lastSample = time_()
			self.wakeUp()
			print(f'{self.name} waking up')
		return None

	def sampling(self, interval=60):
		'''return True after for interval sampling'''

		delta = time_() - self.lastSample
		if (delta > interval) and (self.lastSample >= self.lastTurnOn) :
			# print(f'Time since last sampling {delta}')
			return True
		return False
	
	def warmUp(self, warmup=30):
		'''
		apply for passive mode only, return True after sensor is turned on
		and stablized for a `warmup` period (seconds)
		'''
		if (time_() - self.lastTurnOn > warmup) and (self.lastTurnOn >= self.lastSample):
			return True
		return False
		


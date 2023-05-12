#!/usr/bin/env python
import RPi.GPIO as GPIO
import datetime
import logging
import os
import smbus
import struct
import sys
import time


# Start Config
SHUTDOWN_TRIGGER = "SoC" # (AC Power,SoC,Voltage,All) - determines what settings will trigger a shutdown.
AC_LOSS_WAIT_MINUTES = 15 # Number of minutes after power loss before shutdown is issued
AC_LOSS_TIME = 0 # Time of AC loss moment (epoch)
SOC_THRESHOLD = 10 # Shutdown will occur when SoC drops below the stated percentage
SOC_STATUS_LOW = 20 # Low SoC warning below this level
VOLTAGE_THRESHOLD = 3.40 # Shutdown will occur when voltage drops below the stated percentage
VOLTAGE_STATUS_LOW = 3.20 # Low valtage warning below this level
CHARGING_THRESHOLD = -0.500 # Threshold for battery discharging status
TEST_MODE = False # Will show extra output and will not perform shutdown when set to True, normal opperation TEST_MODE = False
BUZZER_ON = True # Buzzer will beep when power is initially lost and right before shutdown, when set to True
BUZZER_SECONDS = 0.5 # Number of seconds the buzzer will sound
POLLING_TIME = 30 # Number of seconds between each main loop iteration

log = logging.getLogger("x728")
log.setLevel(logging.INFO)
# formatter = logging.Formatter(fmt="%(asctime)s %(name)s.%(levelname)s: %(message)s", datefmt="%Y.%m.%d %H:%M:%S")
formatter = logging.Formatter(fmt="%(name)s.%(levelname)s: %(message)s")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
log.addHandler(handler)

# End Config

WAIT_SECONDS = AC_LOSS_WAIT_MINUTES * 60
WAIT_STR = str(AC_LOSS_WAIT_MINUTES)

GPIO_PORT = 26
I2C_ADDR = 0x36

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PORT, GPIO.OUT)

PLD_PIN = 6
BUZZER_PIN = 20
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PLD_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.output(BUZZER_PIN, 0)

def soundBuzzer(enabled, time_on, pin, times=1):
    if ( enabled ):
        for x in range(times):
            GPIO.output(pin, 1)
            time.sleep(time_on)
            GPIO.output(pin, 0)
            time.sleep(time_on)

def acPower(PLD_PIN):
    AC_STATUS = "GOOD"
    i = GPIO.input(PLD_PIN)
    
    if ( i == 0 ):
        AC_STATUS = "GOOD"
    elif ( i == 1 ):
        AC_STATUS = "LOST"
    
    return AC_STATUS

def readVoltage(bus,VOLTAGE_STATUS_LOW):
    address = I2C_ADDR
    read = bus.read_word_data(address, 2)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    VOLTAGE = swapped * 1.25 /1000/16
    VOLTAGE_STATUS = "GOOD"
    
    if ( VOLTAGE <= VOLTAGE_STATUS_LOW ):
        VOLTAGE_STATUS = "LOW"
        
    return VOLTAGE,VOLTAGE_STATUS

def readSoc(bus,SOC_STATUS_LOW):
    address = I2C_ADDR
    read = bus.read_word_data(address, 4)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    SOC = swapped/256
    SOC_STATUS = "GOOD"
    
    if ( SOC >= 100 ):
        SOC_STATUS = "FULL"
    elif ( SOC <= SOC_STATUS_LOW ):
        SOC_STATUS = "LOW"
        
    return SOC,SOC_STATUS

def readCurrent(bus):
    address = I2C_ADDR
    read = bus.read_word_data(address, 20)
    swapped_as_signed = struct.unpack("<h", struct.pack(">H", read))[0]

    return swapped_as_signed/1000  # [A] units

def safeShutdown(GPIO_PORT):
    GPIO.output(GPIO_PORT, GPIO.HIGH)
    os.system('sudo shutdown -h now')
    time.sleep(3)
    GPIO.output(GPIO_PORT, GPIO.LOW)

bus = smbus.SMBus(1) # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

now = datetime.datetime.now()
date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    
AC_STATUS = acPower(PLD_PIN)
VOLTAGE,VOLTAGE_STATUS = readVoltage(bus, VOLTAGE_STATUS_LOW)
SOC,SOC_STATUS = readSoc(bus, SOC_STATUS_LOW)
CURRENT = readCurrent(bus)

# log.info("******************************************")
log.info("System Startup")
log.info(f"AC Power \t {AC_STATUS}")
log.info(f"Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
log.info(f"Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")
log.info(f"Battery Current \t \t {str(round(CURRENT,3))}A")
log.info(f"Battery Current \t \t {str(round(CURRENT,3))}A")

if ( TEST_MODE ):
    log.info(date_time + " : Started in Test Mode, No actual shutdown will occur, program will exit after shutdown triggered.")


while True:
    # log.info ("******************************************")
    now = datetime.datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")

    AC_STATUS = acPower(PLD_PIN)
    VOLTAGE,VOLTAGE_STATUS = readVoltage(bus, VOLTAGE_STATUS_LOW)
    SOC,SOC_STATUS = readSoc(bus, SOC_STATUS_LOW)
    CURRENT = readCurrent(bus)


    # import web_pdb; web_pdb.set_trace()

    if ( SHUTDOWN_TRIGGER in ["AC Power", "All"] ):
        if ( AC_STATUS == "GOOD" ):
            if ( AC_LOSS_TIME > 0 ):
                log.info(f"AC Power Restored - Shutdown cancelled")
                AC_LOSS_TIME = 0
            else:
                if ( TEST_MODE ):
                    log.info(f"AC Power \t {AC_STATUS}")
        elif ( AC_STATUS == "LOST" ):
            if ( TEST_MODE ):
                log.info(f"AC Power \t {AC_STATUS}")
            if AC_LOSS_TIME == 0:
                AC_LOSS_TIME = time.time()
                log.info(f"AC power lost - shutdown in {AC_LOSS_WAIT_MINUTES} minutes")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=1)
            if ( time.time() >= AC_LOSS_TIME+WAIT_SECONDS):
                log.info(f"Shutdown in progress due to AC power loss after {AC_LOSS_WAIT_MINUTES} minutes...")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=1)
                if ( not TEST_MODE ):
                    safeShutdown(GPIO_PORT)
                else:
                    log.info(f"Started in Test Mode. No actual shutdown will occur, program will exit.")
                    break

    if ( SHUTDOWN_TRIGGER in ["SoC", "All"] ):
        if ( SOC > SOC_THRESHOLD ):
            if ( TEST_MODE ):
                log.info(f"Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
        elif ( SOC <= SOC_THRESHOLD ):
            if ( CURRENT < CHARGING_THRESHOLD ):
                log.info(f"Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
                log.info(f"Shutdown in progress due to battery SoC below threshold ({SOC}<{SOC_THRESHOLD})%")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=2)
                if ( not TEST_MODE ):
                    safeShutdown(GPIO_PORT)
                else:
                    log.info(f"Started in Test Mode. No actual shutdown will occur, program will exit.")
                    break
            else:
                log.info(f"Battery SoC is LOW, but is charging, shutdown cancelled.")

    if ( SHUTDOWN_TRIGGER in ["Voltage", "All"] ):
        if ( VOLTAGE > VOLTAGE_THRESHOLD ):
            if ( TEST_MODE ):
                log.info(f"Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")
        elif ( VOLTAGE <= VOLTAGE_THRESHOLD ):
            if ( CURRENT < CHARGING_THRESHOLD ):
                log.info(f"Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")
                log.info(f"Shutdown in progress due to battery Voltage below threshold ({VOLTAGE}<{VOLTAGE_THRESHOLD})V")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=3)
                if ( not TEST_MODE ):
                    safeShutdown(GPIO_PORT)
                else:
                    log.info(f"Started in Test Mode. No actual shutdown will occur, program will exit.")
                    break
            else:
                log.info(f"Battery Voltage is LOW, but is charging, shutdown cancelled.")

    time.sleep(POLLING_TIME)

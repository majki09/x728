#!/usr/bin/env python
import RPi.GPIO as GPIO
import time
import os
import datetime
import struct
import smbus
import sys


# Start Config
SHUTDOWN_TRIGGER = "All" # (AC Power,SoC,Voltage,All) - determines what settings will trigger a shutdown.
AC_LOSS_WAIT_MINUTES = 15 # Number of minutes after power loss before shutdown is issued
AC_LOSS_TIME = 0 # Time of AC loss moment (epoch)
SOC_THRESHOLD = 20 # Shutdown will occur when SoC drops below the stated percentage
SOC_STATUS_LOW = 20 # Low SoC warning below this level
VOLTAGE_THRESHOLD = 3.20 # Shutdown will occur when voltage drops below the stated percentage
VOLTAGE_STATUS_LOW = 3.20 # Low valtage warning below this level
TEST_MODE = False # Will show extra output and will not perform shutdown when set to True, normal opperation TEST_MODE = False
BUZZER_ON = True # Buzzer will beep when power is initially lost and right before shutdown, when set to True
BUZZER_SECONDS = 0.5 # Number of seconds the buzzer will sound

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

print ("******************************************")
print(date_time + " : System Startup")
print(f"{date_time} : AC Power \t {AC_STATUS}")
print(f"{date_time} : Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
print(f"{date_time} : Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")

if ( TEST_MODE ):
    print(date_time + " : Started in Test Mode, No actual shutdown will occur, program will exit after shutdown triggered.")


while True:
    # print ("******************************************")
    now = datetime.datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")

    AC_STATUS = acPower(PLD_PIN)
    VOLTAGE,VOLTAGE_STATUS = readVoltage(bus, VOLTAGE_STATUS_LOW)
    SOC,SOC_STATUS = readSoc(bus, SOC_STATUS_LOW)


    import web_pdb; web_pdb.set_trace()
    

    if ( SHUTDOWN_TRIGGER in ["AC Power", "All"] ):
        if ( AC_STATUS == "GOOD" ):
            if ( AC_LOSS_TIME > 0 ):
                print(f"{date_time} : AC Power Restored - Shutdown cancelled")
                AC_LOSS_TIME = 0
            else:
                if ( TEST_MODE ):
                    print(f"{date_time} : AC Power \t {AC_STATUS}")
        elif ( AC_STATUS == "LOST" ):
            if ( TEST_MODE ):
                print(f"{date_time} : AC Power \t {AC_STATUS}")
            if AC_LOSS_TIME == 0:
                AC_LOSS_TIME = time.time()
                print(f"{date_time} : AC power lost - shutdown in {AC_LOSS_WAIT_MINUTES} minutes")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=1)
            if ( time.time() >= AC_LOSS_TIME+WAIT_SECONDS):
                print(f"{date_time} : Shutdown in progress due to AC power loss after {AC_LOSS_WAIT_MINUTES} minutes...")
                soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=1)
                if ( not TEST_MODE ):
                    safeShutdown(GPIO_PORT)
                else:
                    print(f"{date_time} : Started in Test Mode. No actual shutdown will occur, program will exit.")
                    break

    if ( SHUTDOWN_TRIGGER in ["SoC", "All"] ):
        if ( SOC > SOC_THRESHOLD ):
            if ( TEST_MODE ):
                print(f"{date_time} : Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
        elif ( SOC <= SOC_THRESHOLD ):
            print(f"{date_time} : Battery SoC \t {SOC_STATUS} \t {str(round(SOC,2))}%")
            print(f"{date_time} : Shutdown in progress due to battery SoC below threshold ({SOC}<{SOC_THRESHOLD})%")
            soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=2)
            if ( not TEST_MODE ):
                safeShutdown(GPIO_PORT)
            else:
                print(f"{date_time} : Started in Test Mode. No actual shutdown will occur, program will exit.")
                break

    if ( SHUTDOWN_TRIGGER in ["Voltage", "All"] ):
        if ( VOLTAGE > VOLTAGE_THRESHOLD ):
            if ( TEST_MODE ):
                print(f"{date_time} : Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")
        elif ( VOLTAGE <= VOLTAGE_THRESHOLD ):
            print(f"{date_time} : Battery Voltage \t {VOLTAGE_STATUS} \t {str(round(VOLTAGE,2))}V")
            print(f"{date_time} : Shutdown in progress due to battery Voltage below threshold ({VOLTAGE}<{VOLTAGE_THRESHOLD})V")
            soundBuzzer(BUZZER_ON, BUZZER_SECONDS, BUZZER_PIN, times=3)
            if ( not TEST_MODE ):
                safeShutdown(GPIO_PORT)
            else:
                print(f"{date_time} : Started in Test Mode. No actual shutdown will occur, program will exit.")
                break

    time.sleep(10)

    # GPIO.cleanup()
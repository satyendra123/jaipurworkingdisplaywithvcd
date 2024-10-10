from machine import Pin, UART
from time import sleep, ticks_ms
import os

# Configuration
entryLoopPin = 5  # Entry loop detector pin
exitLoopPin = 4   # Exit loop detector pin
debounceDelay = 50  # Debounce delay in milliseconds

# Initialize pins
entryLoop = Pin(entryLoopPin, Pin.IN, Pin.PULL_UP)
exitLoop = Pin(exitLoopPin, Pin.IN, Pin.PULL_UP)

# Initialize UART
uart = UART(2, baudrate=9600, tx=Pin(16), rx=Pin(17))
uart2 = UART(1, baudrate=9600, tx=Pin(33), rx=Pin(32))

# Function to read a count from a file
def read_count(file_name):
    try:
        with open(file_name, 'r') as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0

# Function to write a count to a file
def write_count(file_name, count):
    try:
        with open(file_name, 'w') as f:
            f.write(str(count))
        print(f"{file_name} updated: {count}")
    except OSError as e:
        print(f"Failed to write to {file_name}: {e}")

# Function to update metadata file
def save_metadata(metadata):
    try:
        with open('metadata.txt', 'w') as f:
            f.write(f"{metadata['totalSlots']},{metadata['vacantSlots']},{metadata['totalEntry']},{metadata['totalExit']}\n")
        print("Metadata written to filesystem")
    except OSError as e:
        print(f"Failed to write metadata: {e}")

# Function to read metadata file
def read_metadata():
    try:
        with open('metadata.txt', 'r') as f:
            line = f.readline().strip()
            totalSlots, vacantSlots, totalEntry, totalExit = map(int, line.split(','))
            return {'totalSlots': totalSlots, 'vacantSlots': vacantSlots, 'totalEntry': totalEntry, 'totalExit': totalExit}
    except (OSError, ValueError):
        return {'totalSlots': 99, 'vacantSlots': 99, 'totalEntry': 0, 'totalExit': 0}

# Load metadata
metadata = read_metadata()
totalSlots = metadata['totalSlots']
vacantSlots = metadata['vacantSlots']
totalEntry = metadata['totalEntry']
totalExit = metadata['totalExit']

def sendAvailableSlots(slots):
    slots_str = f'{slots:02d}'
    message = f'|C|1|4|1|28-0-#u{slots_str}|'
    print(f"Sending message: {message}")
    uart.write(message.encode('ascii'))

def sendNewUARTData(totalSlots, vacantSlots, totalEntry, totalExit):
    data_array = [0xAA, totalSlots, vacantSlots, totalEntry, totalExit, 0xCC]
    uart2.write(bytearray(data_array))
    print(f"New UART Data Sent: {data_array}")

def printAvailableSlots():
    print("Available Parking Slots:", vacantSlots)

def printTotalSlots():
    print("Total Parking Slots:", totalSlots)

# Print initial available slots
printAvailableSlots()
printTotalSlots()
sendAvailableSlots(vacantSlots)

lastEntryTime = 0
lastExitTime = 0

# Main loop
while True:
    currentTime = ticks_ms()
    
    entryReading = entryLoop.value()
    exitReading = exitLoop.value()
    
    # Handle entry detection
    if entryReading == 0 and (currentTime - lastEntryTime >= debounceDelay):
        sleep(0.05)
        if entryLoop.value() == 0:
            lastEntryTime = currentTime
            if vacantSlots > 0:
                vacantSlots -= 1
                totalEntry += 1
                printAvailableSlots()
                sendAvailableSlots(vacantSlots)
                sendNewUARTData(totalSlots, vacantSlots, totalEntry, totalExit)
                write_count('total_entry.txt', totalEntry)
                metadata['vacantSlots'] = vacantSlots
                metadata['totalEntry'] = totalEntry
                save_metadata(metadata)
                sleep(1)
    
    # Handle exit detection
    if exitReading == 0 and (currentTime - lastExitTime >= debounceDelay):
        sleep(0.05)
        if exitLoop.value() == 0:
            lastExitTime = currentTime
            if vacantSlots < totalSlots:
                vacantSlots += 1
                totalExit += 1
                printAvailableSlots()
                sendAvailableSlots(vacantSlots)
                sendNewUARTData(totalSlots, vacantSlots, totalEntry, totalExit)
                write_count('total_exit.txt', totalExit)
                metadata['vacantSlots'] = vacantSlots
                metadata['totalExit'] = totalExit
                save_metadata(metadata)
                sleep(1)
    
    # Check if data is available on UART
    if uart.any():
        command = uart.read(1)
        if command == b'S':
            total_string = uart.read(3)
            vacant_string = uart.read(3)
            try:
                total = int(total_string)
                vacant = int(vacant_string)
                if total > 0 and 0 <= vacant <= total:
                    totalSlots = total
                    vacantSlots = vacant
                    metadata['totalSlots'] = totalSlots
                    metadata['vacantSlots'] = vacantSlots
                    save_metadata(metadata)
                    print("Total Parking Slots set to:", totalSlots)
                    print("Available Parking Slots set to:", vacantSlots)
                    sendAvailableSlots(vacantSlots)
            except ValueError:
                pass
    
    sleep(0.1)
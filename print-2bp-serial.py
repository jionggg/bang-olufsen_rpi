import serial

# Open the serial port (adjust the port and baud rate as per your setup)
ser = serial.Serial('/dev/ttyUSB0', 3000000)  # Adjust the port and baud rate

print("Waiting for data from UART...")

while True:
    # Read a line from the UART
    line = ser.readline().decode('utf-8').strip()

    # Print the received line to the terminal
    print(line)



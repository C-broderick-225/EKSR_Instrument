import serial
import datetime, threading, time

alist = [b'\x00' * 32] * 32

def open_serial_port(port, baudrate):
    try:
        global ser
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port} at {baudrate} baud.")
        return ser
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return None

def clear_screen():
        print('\x1B[2J')

def goto_line(line):
        print('\x1B[' + str(line) + ';1H')

def set_color(inverse):
    if (inverse):
        print('\x1B[7m', end='')
    else:
        print('\x1B[0m', end='')
    return

def read_from_serial(ser):
    while ser.in_waiting:
        try:
            global alist
            # read 16 bytes total : 0xAA, address, 12 bytes data and 2 bytes checksum
            data = ser.read(16)
            index = data[1]
            if (index < 24):
                goto_line(index + 2)
                set_color(False)
                print('{: >2}'.format(index) + ' : ', end='')
                old = alist[index]
                for i in range(2,14):
                    if (old[i] != data[i]):
                        set_color(True)
                    else:
                        set_color(False)
                    print(format(data[i],'02x') + ' ', end='')
                set_color(False)
                print('')
                alist[index] = data


        except Exception as e:
            print(f"\nError reading from serial: {e}")


def write_to_serial(ser):
    try:
        data = input("Enter data to send: ")
        ser.write(data.encode('utf-8'))
    except Exception as e:
        print(f"Error writing to serial: {e}")

def foo():
    global ser
    if (foo.first):
        keep_alive = [ 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0, 0xF0 ] # size 8
    else:
        keep_alive = [ 0xAA, 0x13, 0xec, 0x07, 0x01, 0xF1, 0xA2, 0x5D ] # size 8
    foo.first = False
    ser.write(keep_alive);
    #print (datetime.datetime.now())
    threading.Timer(2, foo).start()

foo.first = True

def run_serial_terminal(port, baudrate):
    ser = open_serial_port(port, baudrate)
    clear_screen()
    goto_line(1)
    print('      0  1  2  3  4  5  6  7  8  9 10 11')
    print('\x1B[?25l')

    timerThread = threading.Thread(target=foo)
    timerThread.daemon = True
    timerThread.start()

    if ser:
        try:
            while True:
                read_from_serial(ser)
                time.sleep(0.1)  # Adjust the polling rate if needed
        except KeyboardInterrupt:
            print("\nClosing serial connection.")
        finally:
            ser.close()
    else:
        print("Unable to open serial port.")

if __name__ == "__main__":
    run_serial_terminal("/dev/tty.usbserial-834440", 19200)

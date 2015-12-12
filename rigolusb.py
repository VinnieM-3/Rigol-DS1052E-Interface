# Copyright (c) 2015, Vinnie M.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import os
import numpy as np
from time import sleep
import threading


# Make sure usbtmc service running.  On linux: "sudo modprobe usbtmc".
# On Windows use VISA drivers?  Windows untested.

# For linux, may also need /etc/udev/rules.d/usbtmc.rules file containing the following:
# USBTMC instruments
# Rigol DS1052E
# SUBSYSTEMS=="usb", ACTION=="add", ATTRS{idVendor}=="1ab1", ATTRS{idProduct}=="0588", GROUP="usbtmc", MODE="0660"

lock = threading.Lock()


def _send_command(device_file, command, read_bytes=0):
    lock.acquire()
    try:
        sleep(0.020)
        os.write(device_file, bytearray(command, 'ascii'))
        if read_bytes > 0:
            response = os.read(device_file, read_bytes)
            return response
    except:
        raise
    finally:
        lock.release()
        

# Open the device file
def open_device_file(device_path):
    os_file = os.open(device_path, os.O_RDWR)
    return os_file


# Close the device file
def close_device_file(os_file):
    os.close(os_file)


# Stop all acquisition
def set_stop(os_file):
    _send_command(os_file, ":STOP")


# Switch from remote (rmt) control back to local control
def set_local(os_file):
    _send_command(os_file, ":KEY:FORC")


# Get the time-per-division
def get_id(os_file):
    return str(_send_command(os_file, "*IDN?", 2000))


# Get the time-per-division
def get_time_per_division(os_file):
    return float(_send_command(os_file, ":TIM:SCAL?", 20))  


# Get the time-offset
def get_time_offset(os_file):
    return float(_send_command(os_file, ":TIM:OFFS?", 20))  


# Get state of channel
def get_channel_state(os_file, ch_num):
    return int(_send_command(os_file, ":CHAN" + str(ch_num) + ":DISP?", 20))


# Get the channel data
def get_points(os_file, waveform_pnts_mode, ch_num):
    _send_command(os_file, ":WAV:POIN:MODE " + waveform_pnts_mode)
    raw_data = _send_command(os_file, ":WAV:DATA? CHAN"
                             + str(ch_num), 1048586)  # 1048576 + 10 header
    points = np.frombuffer(raw_data, 'B')
    return points[10:]


# Get the channel volts-per-division
def get_volts_div(os_file, ch_num):
    return float(_send_command(os_file, ":CHAN" + str(ch_num) + ":SCAL?", 20))    


# Get the channel vertical-offset
def get_vertical_offset(os_file, ch_num):
    return float(_send_command(os_file, ":CHAN" + str(ch_num) + ":OFFS?", 20))    


# Get the channel sample-rate
def get_sample_rate(os_file, ch_num):
    return float(_send_command(os_file, ":ACQ:SAMP? CHAN" + str(ch_num), 20))    


# Get the channel Vmax
def get_vmax(os_file, ch_num):
    return float(_send_command(os_file, ":MEAS:VMAX? CHAN" + str(ch_num), 20))

    
# Get the channel Vmin
def get_vmin(os_file, ch_num):
    return float(_send_command(os_file, ":MEAS:VMIN? CHAN" + str(ch_num), 20))
     
    
# Get the channel Vpp
def get_vpp(os_file, ch_num):
    return float(_send_command(os_file, ":MEAS:VPP? CHAN" + str(ch_num), 20))


# Get the channel Vamp
def get_vamp(os_file, ch_num):
    vamp = float(_send_command(os_file, ":MEAS:VAMP? CHAN" + str(ch_num), 20))
    try:
        vamp = float(vamp)
        if vamp > 1E9:  # assumed to be an error
            raise ValueError
    except ValueError:
        vamp = '***'
    return vamp


# Get the channel Vrms
def get_vrms(os_file, ch_num):
    return float(_send_command(os_file, ":MEAS:VRMS? CHAN" + str(ch_num), 20))
    
    
# Get the channel Freq
def get_freq(os_file, ch_num):
    freq = _send_command(os_file, ":MEAS:FREQ? CHAN" + str(ch_num), 20)
    try:
        freq = float(freq)
        if freq > 1E9:  # assumed to be an error
            raise ValueError
    except ValueError:
        freq = '********'
    return freq

  
# Get the channel Duty Cycle
def get_duty_cycle(os_file, ch_num):
    pdut = _send_command(os_file, ":MEAS:PDUT? CHAN" + str(ch_num), 20)
    ndut = _send_command(os_file, ":MEAS:NDUT? CHAN" + str(ch_num), 20)
    try:
        pdut = float(pdut)
        ndut = float(ndut)
        pdut *= 100
        ndut *= 100
        pdut = round(pdut, 3)
        ndut = round(ndut, 3)
        if pdut > 100 or ndut > 100:  # assumed to be an error
            raise ValueError
    except ValueError:
        pdut = '***'
        ndut = '***'
    return str(pdut) + '/' + str(ndut)

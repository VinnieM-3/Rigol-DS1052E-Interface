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
# SOFTWAR

import numpy as np
import rigolusb
import datetime

SAMPLES = 'samples'
UNITS = 'units'


class DS1000(object):
    """ Represents the scope itself and has multiple channels """
    
    def __init__(self, device_path, num_channels):
        self._device_path = device_path
        self._os_file = None
        self._num_channels = num_channels
        self._channels = []
        self._active_channels = []
        self._id = ''
        self._retrieval_date = datetime.datetime.now()
        self._waveform_pnts_mode = 'NOR'
        self._time_per_division = 0.0
        self._time_offset = 0.0
        self._time_axis = []
        self._time_units = '(sec)'
        self._points_per_channel = 0
        self._samplerate_per_channel = 0
        for i in range(num_channels):
            self._channels.append(Channel(i+1))

    def query_scope(self, _waveform_pnts_mode='NOR'):
        self._waveform_pnts_mode = _waveform_pnts_mode
        self._os_file = rigolusb.open_device_file(self._device_path)
        rigolusb.set_stop(self._os_file)
        self._retrieval_date = datetime.datetime.now()
        self._id = rigolusb.get_id(self._os_file)
        self._time_per_division = rigolusb.get_time_per_division(self._os_file)
        self._time_offset = rigolusb.get_time_offset(self._os_file)
        self._active_channels = []
        for ch in self._channels:
            ch.load_channel_data(self._os_file, self._waveform_pnts_mode)
            if ch.state == 1:
                self._active_channels.append(ch)
        rigolusb.set_local(self._os_file)
        rigolusb.close_device_file(self._os_file)
        if self.num_active_channels > 0:
            ch = self._active_channels[0]
            self._points_per_channel = ch.num_points
            self._samplerate_per_channel = ch.sample_rate
            res = self._calc_time_axis()
            self._time_axis = res[0]
            self._time_units = res[1]
        else:
            self._points_per_channel = 0
            self._samplerate_per_channel = 0
            self._time_axis = []
            self._time_units = '(sec)'

    def _calc_time_axis(self):
        if self._points_per_channel == 600:
            time_step = self.time_per_division / 50.0
            x_low = (self.time_per_division * -6) + self.time_offset
            x_high = (599 * time_step) + x_low
        else:
            time_step = 1.0 / self._samplerate_per_channel
            x_low = -((self._points_per_channel / 2.0) * time_step) + self.time_offset
            x_high = ((self._points_per_channel - 1) * time_step) + x_low
        time_axis = np.linspace(x_low, (x_high + time_step), self._points_per_channel)

        # Adjust time scale units
        time_avg = (x_high + abs(x_low)) / 2.0
        time_label = '(sec)'
        if time_avg >= 1:
            pass
        elif time_avg >= 0.001:
            time_axis *= 1000
            time_label = '(ms)'
        elif time_avg >= 0.000001:
            time_axis *= 1000000
            time_label = '(us)'
        else:
            time_axis *= 1000000000
            time_label = '(ns)'
        return [time_axis, time_label]

    def get_channel(self, ch_num):
        return self._channels[ch_num-1]

    @property
    def channels(self):
        return self._channels

    @property
    def num_channels(self):
        return self._num_channels

    @property
    def active_channels(self):
        return self._active_channels

    @property
    def num_active_channels(self):
        return len(self._active_channels)

    @property
    def id(self):
        return self._id

    @property
    def retrieval_date(self):
        return self._retrieval_date

    @property
    def waveform_pnts_mode(self):
        return self._waveform_pnts_mode

    @waveform_pnts_mode.setter
    def waveform_pnts_mode(self, value):
        self._waveform_pnts_mode = value

    @property
    def time_per_division(self):
        return self._time_per_division
    
    @property
    def time_offset(self):
        return self._time_offset

    @property
    def time_axis(self):
        return {SAMPLES: self._time_axis, UNITS: self._time_units}

    @property
    def points_per_channel(self):
        return self._points_per_channel

    @property
    def samplerate_per_channel(self):
        return self._samplerate_per_channel


class Channel(object):
    """ Represents one channel on an oscilloscope """

    def __init__(self, ch_num):
        self._ch_num = ch_num
        self._state = 0
        self._raw_points = np.asarray([])
        self._volts_div = 0.0
        self._vert_offset = 0.0
        self._sample_rate = 0.0        
        self._vmax = 0.0
        self._vmin = 0.0
        self._vpp = 0.0
        self._vamp = 0.0
        self._vrms = 0.0
        self._freq = 0.0
        self._duty_cycle = '***/***'
        self._measures_string = ''
        self._num_points_abbr = ''
        self._volt_points = []
        
    def load_channel_data(self, _os_file, _waveform_pnts_mode):
        self._state = rigolusb.get_channel_state(_os_file, self._ch_num)
        if self._state:
            self._raw_points = rigolusb.get_points(_os_file, _waveform_pnts_mode, self._ch_num)
            self._volts_div = rigolusb.get_volts_div(_os_file, self._ch_num)
            self._vert_offset = rigolusb.get_vertical_offset(_os_file, self._ch_num)
            self._sample_rate = rigolusb.get_sample_rate(_os_file, self._ch_num)
            self._vmax = rigolusb.get_vmax(_os_file, self._ch_num)
            self._vmin = rigolusb.get_vmin(_os_file, self._ch_num)
            self._vpp = rigolusb.get_vpp(_os_file, self._ch_num)
            self._vamp = rigolusb.get_vamp(_os_file, self._ch_num)
            self._vrms = rigolusb.get_vrms(_os_file, self._ch_num)
            self._freq = rigolusb.get_freq(_os_file, self._ch_num)
            self._duty_cycle = rigolusb.get_duty_cycle(_os_file, self._ch_num)
            self._measures_string = ('Vmax=' + str(self._vmax) + 'V' + ',  ' +
                                     'Vmin=' + str(self._vmin) + 'V' + ',  ' +
                                     'Vrms=' + str(self._vrms) + 'V' + ',  ' +
                                     'Vamp=' + str(self._vamp) + 'V' + ',  ' +
                                     'Freq=' + str(self._freq) + 'Hz' + ',  ' +
                                     'Duty=' + str(self._duty_cycle) + '%')
            if self.num_points == 600:
                self._num_points_abbr = '600'
            elif self.num_points == 8192:
                self._num_points_abbr = '8K'
            elif self.num_points == 16384:
                self._num_points_abbr = '16K'
            elif self.num_points == 524288:
                self._num_points_abbr = '512K'
            elif self.num_points == 1048576:
                self._num_points_abbr = '1M'
            else:
                self._num_points_abbr = str(self.num_points)

            self._volt_points = 5 * self._volts_div - 0.04 * self._volts_div * self._raw_points - self._vert_offset
        else:
            self._raw_points = np.asarray([])
            self._volts_div = 0.0
            self._vert_offset = 0.0
            self._sample_rate = 0.0
            self._vmax = 0.0
            self._vmin = 0.0
            self._vpp = 0.0
            self._vamp = 0.0
            self._vrms = 0.0
            self._freq = 0.0
            self._duty_cycle = '***/***'
            self._measures_string = ''
            self._num_points_abbr = ''
            self._volt_points = []

    @property
    def ch_num(self):
        return self._ch_num

    @property
    def state(self):
        return self._state

    @property
    def raw_points(self):
        return self._raw_points
    
    @property
    def volts_div(self):
        return self._volts_div

    @property
    def vert_offset(self):
        return self._vert_offset

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def vmax(self):
        return self._vmax

    @property
    def vmin(self):
        return self._vmin

    @property
    def vpp(self):
        return self._vpp

    @property
    def vamp(self):
        return self._vamp

    @property
    def vrms(self):
        return self._vrms
    
    @property
    def freq(self):
        return self._freq
    
    @property
    def duty_cycle(self):
        return self._duty_cycle

    @property
    def meas_string(self):
        return self._measures_string
   
    @property
    def num_points(self):
        return len(self._raw_points)

    @property
    def num_points_abbr(self):
        return self._num_points_abbr
   
    @property
    def volt_points(self):
        return self._volt_points

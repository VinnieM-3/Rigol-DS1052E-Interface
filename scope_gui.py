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

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import argparse
from matplotlib import gridspec
import scope
import shelve


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--device', help='device path.  ex. "/dev/usbtmc1", default is /dev/usbtmc1', required=False,
                    default='/dev/usbtmc1')

parser.add_argument('-p', '--printfriendly', help='Uses white background and black lines and text',
                    action="store_true")

parser.add_argument('-m', '--mode', help='Wave Point Mode setting', required=False, default='RAW',
                    choices=['NOR', 'RAW'])  # NOR limits to 600 points and shows measurements

parser.add_argument('-s', '--style', help='Graph data using dots or lines', required=False, default='lines',
                    choices=['lines', 'dots'])

parser.add_argument('-i', '--input', help='Import data from file', required=False, default='')

parser.add_argument('-o', '--output', help='Save data to file', required=False, default='')

args = parser.parse_args()
device_path = args.device
printer_friendly = args.printfriendly
waveform_pnts_mode = args.mode
graph_style = args.style
input_file = args.input
output_file = args.output


# Adjust chunksize for large number of data points.
mpl.rcParams['agg.path.chunksize'] = 20000

scp = None
if len(input_file) > 0:
    # Import scope data from file
    db = shelve.open(input_file)
    scp = db['scope']
    db.close()
else:
    # Create scope object and retrieve data
    scp = scope.DS1000(device_path, 2)
    scp.query_scope(waveform_pnts_mode)
if len(output_file) > 0:
    # Export scope data to file
    db = shelve.open(output_file)
    db['scope'] = scp
    db.close()

# Create figure and use date and time as title which doubles as default filename when saving image.
fig = plt.figure(scp.retrieval_date.strftime("%Y%m%d_%H%M%S") + "_scope_output")
fig.suptitle(scp.retrieval_date.strftime("     %x   %X"), weight='bold')


# Depicts waveform window in memory similar to top center graphic on Rigol scope.
def draw_mem_map(ax, ch_ax):
    ax.set_title("Waveform Window in Memory")
    ax.tick_params(axis='both', which='both', bottom='off', top='off',
                   left='off', right='off', labelleft='off', labelbottom='off')
    ax.set_xlim(scp.time_axis[scope.SAMPLES][0], scp.time_axis[scope.SAMPLES][len(scp.time_axis[scope.SAMPLES])-1])
    ax.plot(np.asarray([scp.time_axis[scope.SAMPLES][0],
            scp.time_axis[scope.SAMPLES][len(scp.time_axis[scope.SAMPLES])-1]]),
            np.asarray([1, 1]), lw=1, color='black')
    return ax.plot(np.asarray(ch_ax.get_xlim()), np.asarray([1, 1]), lw=3, marker='s', color='black')


# Graphs channel data
def draw_ch(ch, ch_ax, num, x_min, x_max, ax_color, fig_bg_color, grid_color):
    ch_ax.margins(y=0.2)
    ch_ax.set_title("Channel " + str(num))
    ch_ax.set_xlabel("Time " + scp.time_axis[scope.UNITS])
    ch_ax.set_ylabel("Voltage (V)")
    if ch.state and ch.num_points == 600:
        ch_ax.text(0.01, 0.01, ch.meas_string, ha="left", va="bottom", size='small',
                   transform=ch_ax.transAxes, color=ax_color)
    ch_ax.set_axis_bgcolor(fig_bg_color)
    if graph_style == 'lines':
        ch_ax.plot(scp.time_axis[scope.SAMPLES], ch.volt_points, color=ax_color)
    elif graph_style == 'dots':
        ch_ax.plot(scp.time_axis[scope.SAMPLES], ch.volt_points, linestyle='', marker='.', color=ax_color)
    ch_ax.grid(color=grid_color)
    ch_ax.set_xlim(scp.time_axis[scope.SAMPLES][x_min], scp.time_axis[scope.SAMPLES][x_max])
    ch_ax.text(0.99, 0.98, ch.num_points_abbr + " Points", ha="right", va="top", size='small',
               transform=ch_ax.transAxes, color=ax_color)


# Updates Waveform Memory Map
def on_draw(event):
    if scp.num_active_channels > 0:
        map_x_raw = mem_ax_lines[0].get_xdata()
        ch_x_raw = ch_ax_ref.get_xlim()
        map_x_rnd = (round(map_x_raw[0], 6), round(map_x_raw[1], 6))
        ch_x_rnd = (round(ch_x_raw[0], 6), round(ch_x_raw[1], 6))
        if map_x_rnd != ch_x_rnd:
            mem_ax_lines[0].set_xdata(np.asarray(ch_ax_ref.get_xlim()))
            gs.tight_layout(fig, rect=[0.01, 0, 1, 0.95])
            plt.draw()
fig.canvas.mpl_connect('draw_event', on_draw)


# Maximizes plots in figure canvas.
def on_resize(event):
    gs.tight_layout(fig, rect=[0.01, 0, 1, 0.95])
    fig.canvas.draw_idle()
fig.canvas.mpl_connect('resize_event', on_resize)


# Set colors based on whether we intend to print or just view on monitor
fig_bg_color = 'black'
grid_color = 'white'
plot_colors = ['yellow', 'cyan', 'deeppink', 'lightblue']
# added two extra colors (deeppink and lightblue) in hopes of supporting 4ch scope in the future.
if printer_friendly:
    fig_bg_color = 'white'
    grid_color = 'black'
    plot_colors = ['black', 'black', 'black', 'black']


# Calculate min and max initial display points so that amount of data displayed matches scope.
if scp.points_per_channel == 600:  # zoom out to all points
    x_min = 0
    x_max = 599
else:
    x_mid = round(len(scp.time_axis[scope.SAMPLES])/2)
    total_points_displayed = (scp.time_per_division * 12) * scp.samplerate_per_channel
    x_min = x_mid - round(total_points_displayed/2)
    x_max = x_mid + round(total_points_displayed/2)
    if x_min < 0:
        x_min = 0
    if x_max > (len(scp.time_axis[scope.SAMPLES])-1):
        x_max = len(scp.time_axis[scope.SAMPLES])-1

# Time to start ploting channel data
if scp.num_active_channels > 0:
    h_ratios = []
    map_ratio = round((scp.num_active_channels * 20) / 12.0)
    h_ratios.append(map_ratio)
    for x in range(scp.num_active_channels):
        h_ratios.append(20)

    gs = gridspec.GridSpec(scp.num_active_channels + 1, 1, height_ratios=h_ratios)
    num = 1
    ch_ax_ref = None
    for ch in scp.active_channels:
        if num == 1:
            ch_ax = fig.add_subplot(gs[num])
            ch_ax_ref = ch_ax
            mem_ax_lines = draw_mem_map(fig.add_subplot(gs[0]), ch_ax_ref)
        else:
            ch_ax = fig.add_subplot(gs[num], sharex=ch_ax_ref)
        draw_ch(ch, ch_ax, ch.ch_num, x_min, x_max, plot_colors[ch.ch_num - 1], fig_bg_color, grid_color)
        num += 1
else:
    gs = gridspec.GridSpec(1, 1)
    fig.add_subplot(gs[0])
    plt.figtext(0.45, 0.5, ' Both Channels Off', color='black', weight='roman', size='small')


plt.show()

import os.path
import logging
from collections import deque
import numpy as np
from scipy.sparse import csr_matrix
import sys
from typing import List, Dict
from dataclasses import dataclass
# from utils import divide_csr


# TODO: split the definition parsing
def parse_definitions(defn_lines):
    pass


@dataclass(frozen=True)
class Event:
    time: int
    value: int


def read_toggles_vcd(vcd_filename, signal_filter=None, clock=1000, window=1):
    logging.info("VCD file: %s, Window: %d", vcd_filename, window)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename
    cycle = 0
    reset_cycle = 0

    symbols = dict()        # type: Dict[str, int] # symbol -> idx
    bus_signals = list()    # type: List[str]
    bus_toggles = list()    # type: List[deque]
    bus_indices = list()    # type: List[deque]
    widths = list()         # type: List[int]

    vcd_data = None         # type: List[List[Event]]

    time = -1
    with open(vcd_filename, "r") as _f:
        path = list()           # type: List[str]
        clock_value = None      # type: int
        clock_symbol = None     # type: str
        reset_value = None      # type: int
        reset_symbol = None     # type: str

        for line in _f:
            tokens = line.split()
            if not tokens:
                pass
            elif tokens[0][0] == "$":
                # module instance
                if tokens[0] == "$scope":
                    assert tokens[1] == "module"
                    assert tokens[3] == "$end"
                    path.append(tokens[2])
                # move up to the upper module instance
                elif tokens[0] == "$upscope":
                    path = path[:-1]
                # signal definition
                elif tokens[0] == "$var":
                    width = int(tokens[2])
                    symbol = tokens[3]
                    signal_name = tokens[4]
                    signal = ("%s.%s" % (".".join(path), signal_name))
                    if signal_name == "clock":
                        clock_symbol = symbol
                        clock_value = '0'
                    elif signal_name == "reset":
                        reset_symbol = symbol
                    # TODO: refine this (maybe use the signal filter)
                    elif ("clock" in signal or "reset" in signal
                            or "_clk" in signal or "_rst" in signal
                            or "initvar" in signal or "_RAND" in signal
                            or "_GEN_" in signal):  # FIXME: due to circuit mismatch
                        pass
                    # TODO: annotate what this does exactly, generalize the above case into signal_filter
                    elif signal_filter and signal not in signal_filter:
                        pass
                    elif symbol not in symbols:
                        symbols[symbol] = len(bus_signals)
                        widths.append(width)
                        bus_signals.append(signal)
                        bus_toggles.append(deque())
                        bus_indices.append(deque())
                    elif symbol in symbols:
                        assert False, "I've already seen this symbol {} for signal {}".format(symbol, signal)
                # no more variable definitions
                elif tokens[0] == "$enddefinitions":
                    assert tokens[1] == "$end"
                    has_toggled = [False] * len(bus_signals)
                    cur_toggles = [0] * len(bus_signals)
                    cur_values = [0] * len(bus_signals)
                    prev_values = [0] * len(bus_signals)
                    path = list()
                    print("$enddefinitions - bus_signals: {}".format(list(zip(bus_signals, widths))))

            # TODO: parse $dumpvars section for initial values of signals
            elif tokens[0][0] == '#':
                # simulation time
                time = int(tokens[0][1:])
                # Clock Tick
                if cycle > 0 and clock_value == '1':
                    if reset_value == '1':
                        reset_cycle += 1
                    # update toggles
                    for i, _t in enumerate(has_toggled):
                        if _t:
                            width = widths[i]
                            value = cur_values[i]
                            bus_diff = bin(value ^ prev_values[i]).count('1')
                            cur_toggles[i] += bus_diff
                            prev_values[i] = value
                            has_toggled[i] = False

                    if reset_value == '0' and ((cycle - reset_cycle) % window == 0):
                        idx = (cycle - reset_cycle) / window - 1
                        for i, (ids, ts, width) in enumerate(
                                zip(bus_indices, bus_toggles, widths)):
                            if cur_toggles[i] > 0:
                                ids.append(idx)
                                ts.append(cur_toggles[i])
                                # ts.append(float(cur_toggles[i]) / (window * width))
                                cur_toggles[i] = 0
            elif time >= 0 and tokens:
                #################
                # Update Values #
                #################
                if len(tokens) == 2:
                    assert tokens[0][0] == 'b'
                    value = tokens[0][1:]
                    symbol = tokens[1]
                elif len(tokens) == 1:
                    value = tokens[0][0]
                    symbol = tokens[0][1:]
                #assert cycle == 0 or time % clock == 0 or \
                #  symbol == clock_symbol or symbol == reset_symbol, \
                #  "time: %d, clock: %d, symbol: %s" % (time, clock, symbol)
                if symbol == clock_symbol:
                    clock_value = value
                    if time > 0 and clock_value == '1':
                        # clock tick
                        cycle += 1
                if symbol == reset_symbol:
                    reset_value = value
                elif cycle > 0 and clock_value == '1' and symbol in symbols:
                    # RTL signals tick at clock pos edges
                    idx = symbols[symbol]
                    try:
                        cur_values[idx] = int(value, 2)
                    except ValueError:
                        cur_values[idx] = int(value.replace('x', '0'), 2)
                    has_toggled[idx] = True

    # Leftovers
    tail = (cycle - reset_cycle) % window
    if tail != 0:
        idx = (cycle - reset_cycle - 1) / window
        for i, (ids, ts, width) in enumerate(zip(bus_indices, bus_toggles, widths)):
            if cur_toggles[i] > 0:
                ids.append(idx)
                ts.append(cur_toggles[i])
                # ts.append(float(cur_toggles[i]) / (width * tail))
                cur_toggles[i] = 0

    indptr = [0]
    for bus_index in bus_indices:
        indptr.append(indptr[-1] + len(bus_index))

    indices = list()
    toggles = list()
    for bus_index in bus_indices:
        indices.extend(bus_index)
    for bus_toggle in bus_toggles:
        toggles.extend(bus_toggle)

    widths = np.array(widths)
    indptr = np.array(indptr, dtype=np.int64)
    indices = np.array(indices, dtype=np.int64)
    shape = len(bus_signals), int((cycle - reset_cycle - 1) / window) + 1
    #print(toggles)
    data = csr_matrix((toggles, indices, indptr), shape=shape)
    #data = divide_csr(data, window * widths.reshape(-1, 1))

    return cycle, reset_cycle, bus_signals, data, widths


if __name__ == "__main__":
    read_toggles_vcd(sys.argv[1])

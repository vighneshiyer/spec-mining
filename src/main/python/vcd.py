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


def read_toggles_vcd(vcd_filename, signal_filter=None):
    logging.info("VCD file: %s", vcd_filename)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename

    time = -1  # type: int
    cycle = 0  # type: int
    reset_cycle = 0  # type: int

    symbols = dict()        # type: Dict[str, int] # symbol -> idx in bus_signals, widths, vcd_data
    bus_signals = list()    # type: List[str]
    widths = list()         # type: List[int]
    vcd_data = None         # type: List[List[Event]]

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
                    elif symbol in symbols:
                        assert False, "I've already seen this symbol {} for signal {}".format(symbol, signal)
                # no more variable definitions
                elif tokens[0] == "$enddefinitions":
                    assert tokens[1] == "$end"
                    vcd_data = [[] for _ in range(len(bus_signals))]
            # TODO: parse $dumpvars section for initial values of signals
            elif tokens[0][0] == '#':
                time = int(tokens[0][1:])
                if cycle > 0 and clock_value == 1:
                    if reset_value == 1:
                        reset_cycle += 1
            elif time >= 0 and tokens:
                if len(tokens) == 2:
                    assert tokens[0][0] == 'b'
                    value = int(tokens[0][1:], 2)
                    symbol = tokens[1]
                else:  # len(tokens) == 1
                    assert len(tokens) == 1
                    value = int(tokens[0][0])
                    symbol = tokens[0][1:]

                # BUG: if the clock symbol order is before the signal of interest, clock_value = 1 will be updated too late
                # OK to solve this properly, we just need to parse first, then filter later
                if symbol == clock_symbol:
                    clock_value = value
                    if time > 0 and clock_value == 1:
                        # clock tick
                        cycle += 1
                elif symbol == reset_symbol:
                    reset_value = value
                elif cycle > 0 and clock_value == 1 and symbol in symbols:
                    # RTL signals tick at clock pos edges
                    print(symbol)
                    #assert symbol in symbols
                    idx = symbols[symbol]
                    vcd_data[idx].append(Event(time, value))

    print(vcd_data)
    print("$enddefinitions - bus_signals: {}".format(list(zip(bus_signals, widths))))
    print(vcd_data[bus_signals.index("GCD.io_outputValid")])

    return vcd_data


if __name__ == "__main__":
    read_toggles_vcd(sys.argv[1])

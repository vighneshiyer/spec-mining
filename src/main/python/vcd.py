import sys
import os.path
import logging
from typing import List, Dict
from dataclasses import dataclass


# TODO: split the definition parsing
def parse_definitions(defn_lines):
    pass


@dataclass(frozen=True)
class Event:
    time: int
    value: int


def read_toggles_vcd(vcd_filename: str, signal_filter: List[str]=['_RAND', '_GEN']):
    logging.info("VCD file: %s", vcd_filename)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename

    time = -1               # type: int
    symbols = dict()        # type: Dict[str, int] # symbol -> idx in bus_signals, widths, vcd_data
    bus_signals = list()    # type: List[str]
    widths = list()         # type: List[int]
    vcd_data = None         # type: List[List[Event]]

    with open(vcd_filename, "r") as _f:
        path = list()       # type: List[str]
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
                    if any([signal in x for x in signal_filter]):
                        continue
                    elif symbol not in symbols:
                        symbols[symbol] = len(bus_signals)
                        widths.append(width)
                        bus_signals.append(signal)
                    else:
                        assert symbol not in symbols, "I've already seen this symbol {} for signal {}".format(symbol, signal)
                # no more variable definitions
                elif tokens[0] == "$enddefinitions":
                    assert tokens[1] == "$end"
                    vcd_data = [[] for _ in range(len(bus_signals))]
            # TODO: parse $dumpvars section for initial values of signals
            elif tokens[0][0] == '#':
                time = int(tokens[0][1:])
            elif time >= 0 and tokens:
                if len(tokens) == 2:
                    assert tokens[0][0] == 'b'
                    value = int(tokens[0][1:], 2)
                    symbol = tokens[1]
                else:  # len(tokens) == 1
                    assert len(tokens) == 1
                    value = int(tokens[0][0])
                    symbol = tokens[0][1:]
                assert symbol in symbols
                idx = symbols[symbol]
                vcd_data[idx].append(Event(time, value))

    return bus_signals, widths, vcd_data


if __name__ == "__main__":
    # BUG: if the clock symbol order is before the signal of interest, clock_value = 1 will be updated too late
    # OK to solve this properly, we just need to parse first, then filter later
    bus_signals, widths, vcd_data = read_toggles_vcd(sys.argv[1])

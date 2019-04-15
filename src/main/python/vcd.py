import os.path
import logging
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    time: int
    value: int


@dataclass(frozen=True)
class Signal:
    name: str
    width: int


# There is a bug in the original version of read_vcd where if the clock symbol appears before the signal of interest
# clock_value = 1 will be updated too late, and the signal toggle won't be caught (for signals driven on
# negative edges from chisel-iotesters drivers. This may be an issue with internal signals too, but it
# depends on the specifics of how the VCD is dumped from verilator.
def read_vcd(vcd_filename: str, signal_filter: Set[str]) -> Dict[Signal, List[Event]]:
    logging.info("VCD file: %s", vcd_filename)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename

    time = -1               # type: int
    symbols = dict()        # type: Dict[str, int] # symbol -> idx in bus_signals, widths, vcd_data
    ignore_symbols = set()  # type: Set[str]
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
                    if any([x in signal for x in signal_filter]):
                        ignore_symbols.add(symbol)
                        continue
                    if symbol not in symbols:
                        symbols[symbol] = len(bus_signals)
                        widths.append(width)
                        bus_signals.append(signal)
                    else:
                        print("Found alias for signal {} as {}, ignoring".format(bus_signals[symbols[symbol]], signal))
                        #assert symbol not in symbols, "I've already seen this symbol {} for signal {}".format(symbol, signal)
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
                if symbol in ignore_symbols:
                    continue
                assert(symbol in symbols)
                idx = symbols[symbol]
                vcd_data[idx].append(Event(time, value))

    return {Signal(s[0], s[1]): s[2] for s in zip(bus_signals, widths, vcd_data)}

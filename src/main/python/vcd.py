import os.path
import logging
from typing import List, Dict, Set, Tuple, FrozenSet
from dataclasses import dataclass
from collections import defaultdict


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
# depends on the specifics of how the VCD is dumped from verilator. Solution: sample with a clock after
# the entire VCD parsing is done.

# There's another bug with signal_filter where a signal may have many aliases where a few have junk names (_T)
# and one has a real name (wr_en). If we cut out the symbol too early when seeing an aliased name, we may not
# record a signal which should have been recorded. Solution: strip signals after the VCD data is constructed.
def read_vcd(vcd_filename: str) -> Dict[FrozenSet[Signal], List[Event]]:
    logging.info("VCD file: %s", vcd_filename)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename

    time = -1               # type: int
    # Maps a symbol to a set of aliased signals and the signal's delta event trace.
    # The Set[Signal] contains all the signals in the VCD that were aliased to one logical signal.
    vcd_data = defaultdict(lambda: (set(), []))  # type: Dict[str, Tuple[Set[Signal], List[Event]]]

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
                    vcd_data[symbol][0].add(Signal(signal, width))
                # no more variable definitions
                elif tokens[0] == "$enddefinitions":
                    assert tokens[1] == "$end"
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
                vcd_data[symbol][1].append(Event(time, value))
    return {frozenset(data[0]): data[1] for (symbol, data) in vcd_data.items()}

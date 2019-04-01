import sys
import os.path
import logging
from typing import List, Dict, Set
from dataclasses import dataclass


# TODO: split the definition parsing
def parse_definitions(defn_lines):
    pass


@dataclass(frozen=True)
class Event:
    time: int
    value: int


def read_toggles_vcd(vcd_filename: str, signal_filter: Set[str]={'_RAND', '_GEN'}):
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


def sample_signal(sampling_times: List[int], signal: List[Event]) -> List[Event]:
    """
    Samples a signal at the times given (typically immediately after the rising edge of a clock)
    Will throw an error if any sampling time is ambiguous
    :param sampling_times:
    :param signal:
    :return:
    """
    sig_value = 0
    sampled_signal = []
    while len(sampling_times) > 0:
        if len(signal) == 0 or sampling_times[0] < signal[0].time:
            if len(sampled_signal) > 0 and sampled_signal[-1].value != sig_value:
                sampled_signal.append(Event(sampling_times[0], sig_value))
            elif len(sampled_signal) == 0:
                sampled_signal.append(Event(sampling_times[0], sig_value))
            sampling_times.pop(0)
        elif sampling_times[0] > signal[0].time:
            sig_value = signal[0].value
            signal.pop(0)
        else:
            assert False, "Overlapped signal and sampling time"
    return sampled_signal


if __name__ == "__main__":
    # Notes:
    #   - There is a bug in the original version where if the clock symbol appears before the signal of interest
    #     clock_value = 1 will be updated too late, and the signal toggle won't be caught (for signals driven on
    #     negative edges from chisel-iotesters drivers.
    bus_signals, widths, vcd_data = read_toggles_vcd(sys.argv[1])

    # Only sample signals at rising edge of the clock
    # TODO: Only pick out the top-level clock
    clocks = list(filter(lambda x: 'clock' in x[1], enumerate(bus_signals)))
    assert len(clocks) == 1, "Found too many or no clocks. Got: {}".format(clocks)

    clock_idx = int(clocks[0][0])
    print("Found clock {}".format(bus_signals[clock_idx]))
    clock_posedges = list(map(lambda x: Event(x.time + 1, x.value), filter(lambda x: x.value == 1, vcd_data[clock_idx])))

    test = False
    if test:
        # Case 1: data changes at same timestep as clock
        toy_clock = [Event(1 + x*5, int(x % 2 != 0)) for x in range(10)]
        toy_sampling_times = list(map(lambda x: x.time + 1, filter(lambda x: x.value == 1, toy_clock)))
        toy_data = [Event(2, 1), Event(18, 0)]
        print(toy_sampling_times)
        print(sample_signal(toy_sampling_times, toy_data))
        # TODO: Case 2: data changes at negedge of clock

    # Sample signals right after the clock rising edge (let's just say 1ns after)
    #print(bus_signals)
    #print(vcd_data[bus_signals.index('GCD.io_outputValid')])
    #print(vcd_data[bus_signals.index('GCD.io_loadingValues')])
    print(sample_signal(list(map(lambda x: x.time, clock_posedges)), vcd_data[bus_signals.index('GCD.io_loadingValues')]))

    # Mine: a A a, a alternates with b where a and b are delta events

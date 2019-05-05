import os.path
import logging
from typing import List, Dict, Tuple, FrozenSet, Set
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    time: int
    value: int


@dataclass(frozen=True)
class Signal:
    name: str
    width: int


class Module:
    def __init__(self, name: str) -> None:
        self.name = name
        self.children = []  # type: List[Module]

    def str_helper(self, depth):
        if len(self.children) == 0:
            s = self.name
        else:
            child_strs = ["  "*depth + c.str_helper(depth+1) for c in self.children]
            s = self.name + "\n" + "\n".join(child_strs)
        return s

    def __str__(self):
        return self.str_helper(1)

    def __repr__(self):
        return self.str_helper(1)


AliasedSignals = FrozenSet[Signal]
DeltaTrace = List[Event]
VCDData = Dict[AliasedSignals, DeltaTrace]


# There is a bug in the original version of read_vcd where if the clock symbol appears before the signal of interest
# clock_value = 1 will be updated too late, and the signal toggle won't be caught (for signals driven on
# negative edges from chisel-iotesters drivers (and maybe others). This may be an issue with internal signals too,
# but it depends on the specifics of how the VCD is dumped from verilator. Solution: sample with a clock after
# the entire VCD parsing is done.

# There's another bug with signal_filter where a signal may have many aliases where a few have junk names (_T)
# and one has a real name (wr_en). If we cut out the symbol too early when seeing an aliased name, we may not
# record a signal which should have been recorded. Solution: strip signals after the VCD data is constructed.
def read_vcd(vcd_filename: str) -> Tuple[Module, VCDData]:
    logging.info("VCD file: %s", vcd_filename)
    assert os.path.isfile(vcd_filename), "%s not found" % vcd_filename

    time = -1               # type: int
    # Maps a symbol to a set of aliased signals and the signal's delta event trace.
    # The List[Signal] contains all the signals in the VCD that were aliased to one logical signal.
    vcd_data = defaultdict(lambda: ([], []))  # type: Dict[str, Tuple[List[Signal], List[Event]]]

    with open(vcd_filename, "r") as _f:
        path = list()       # type: List[str]
        module_tree = []    # type: List[Module]
        for line in _f:
            tokens = line.split()
            if not tokens:
                pass
            elif tokens[0][0] == "$":
                # module instance
                if tokens[0] == "$scope":
                    assert tokens[1] == "module"
                    assert tokens[3] == "$end"
                    assert tokens[3] == "$end"
                    path.append(tokens[2])
                    if len(module_tree) > 0:
                        this_module = Module(module_tree[-1].name + "." + tokens[2])
                        module_tree[-1].children.append(this_module)
                        module_tree.append(this_module)
                    else:  # This is the top-level module
                        this_module = Module(tokens[2])
                        module_tree.append(this_module)
                # move up to the upper module instance
                elif tokens[0] == "$upscope":
                    path = path[:-1]
                    if len(module_tree) > 1:  # Don't remove the top-level module from the stack
                        module_tree = module_tree[:-1]
                # signal definition
                elif tokens[0] == "$var":
                    width = int(tokens[2])
                    symbol = tokens[3]
                    signal_name = tokens[4]
                    signal = ("%s.%s" % (".".join(path), signal_name))
                    vcd_data[symbol][0].append(Signal(signal, width))
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

    assert len(module_tree) == 1
    final_module_tree = module_tree[0]
    print("Module hierarchy: \n{}".format(final_module_tree))
    return final_module_tree, {frozenset(data[0]): data[1] for (symbol, data) in vcd_data.items()}


def sample_signal(clock: List[Event], signal: List[Event]) -> List[Event]:
    """
    Samples a signal at the posedge of the clock. The rising edge of the clock will be internally
    brought back by a nudge to sample signals that change on the clock edge.
    """
    posedges = list(filter(lambda e: e.value == 1, clock))
    sig_value = signal[0].value
    assert signal[0].time == 0, "The signal to be sampled requires an initial value"
    clk_idx, sig_idx = 0, 0
    sampled_signal = []  # type: List[Event]

    def add_event(time: int, value: int):
        if len(sampled_signal) > 0 and sampled_signal[-1].value != value:
            sampled_signal.append(Event(time, value))
        elif len(sampled_signal) == 0:
            sampled_signal.append(Event(time, value))

    while sig_idx < len(signal) or clk_idx < len(posedges):
        # signal and clock coincide, so log the signal before the clock edge
        if sig_idx < len(signal) and clk_idx < len(posedges) and signal[sig_idx].time == posedges[clk_idx].time:
            add_event(signal[sig_idx].time, sig_value)
            sig_value = signal[sig_idx].value
            sig_idx = sig_idx + 1
            clk_idx = clk_idx + 1
        # signal toggled 'before' a rising edge, just update the current signal value
        elif (sig_idx < len(signal) and clk_idx < len(posedges) and signal[sig_idx].time < posedges[clk_idx].time) \
                or (clk_idx == len(posedges) and sig_idx < len(signal)):
            sig_value = signal[sig_idx].value
            sig_idx = sig_idx + 1
        # clock posedge has arrived before the next signal transition, so log an event now
        elif (sig_idx < len(signal) and clk_idx < len(posedges) and signal[sig_idx].time > posedges[clk_idx].time) \
                or (sig_idx == len(signal) and clk_idx < len(posedges)):
            add_event(posedges[clk_idx].time, sig_value)
            clk_idx = clk_idx + 1
        else:
            assert False
    return sampled_signal


# An extended version of read_vcd which performs common tasks on the raw VCD data after reading it
# 1. Nudges delta events to occur on a rising clock edge (for consistent post-processing)
# 2. Strips events before a given start_time
# 3. Deletes Chisel temporary/junk signals
# 4. Deletes signals that are wider than signal_bit_limit
def read_vcd_clean(vcd_file_path: str, start_time: int, signal_bit_limit: int) -> Tuple[Module, VCDData]:
    module_tree, vcd_data = read_vcd(vcd_file_path)

    # TODO: Only pick out the top-level clock, this doesn't work for rocket-chip
    clocks = list(filter(
        lambda aliased_signals: any(['clk' in signal.name or 'clock' in signal.name for signal in aliased_signals]),
        vcd_data.keys()))
    assert len(clocks) == 1, "Found too many or no clocks. Got: {}".format(clocks)
    assert all([c.width == 1 for c in clocks[0]]), "All clock signals better have a width of 1"
    clock = clocks[0]
    print("Found clock {}".format(clock))

    # Sample signals on the clock
    vcd_data_sampled = {signal: sample_signal(vcd_data[clock], data) for (signal, data) in vcd_data.items()}
    # Remove the clock from the vcd data
    del vcd_data_sampled[clock]

    # Trim off events before the start_time commandline arg
    for signal, events in vcd_data_sampled.items():
        vcd_data_sampled[signal] = list(filter(lambda e: e.time > start_time, events))

    # Delete keys entirely that consist of *only* Chisel temporary/junk signals
    # Trim all other keys of signals which are Chisel temporary/junk signals
    keys_to_delete = []  # type: List[FrozenSet[Signal]]
    keys_to_trim = {}  # type: Dict[FrozenSet[Signal], Set[Signal]]

    def ignore_sig(sig: Signal) -> bool:
        signals_to_ignore = {'_RAND', '_GEN', '_T', 'reset'}
        return any([ignore_str in sig.name for ignore_str in signals_to_ignore])

    for signal_set in vcd_data_sampled.keys():
        ignored_signals = set(filter(lambda sig: ignore_sig(sig), signal_set))
        if len(ignored_signals) == len(signal_set):
            # If all Signals in this key are junk, then delete the entire key
            keys_to_delete.append(signal_set)
        else:
            # Otherwise, only some Signals in this key need to be junked
            keys_to_trim[signal_set] = ignored_signals

    for key_to_delete in keys_to_delete:
        del vcd_data_sampled[key_to_delete]

    for (key_to_trim, set_of_junk_signals) in keys_to_trim.items():
        new_set = key_to_trim - set_of_junk_signals
        vcd_data_sampled[new_set] = vcd_data_sampled.pop(key_to_trim)

    # Trim off signals that have no delta events or are too wide
    vcd_data_cleaned = {signal_set: trace for (signal_set, trace) in vcd_data_sampled.items()
                        if len(trace) > 0 and list(signal_set)[0].width <= signal_bit_limit}
    return module_tree, vcd_data_cleaned


if __name__ == "__main__":
    print("TESTING: sample_signal")
    # Case 1: data changes at same timestep as clock
    clock = [Event(0, 0), Event(1, 1), Event(2, 0), Event(3, 1), Event(4, 0), Event(5, 1)]
    data = [Event(0, 100), Event(1, 200), Event(5, 300)]
    sampled_data = sample_signal(clock, data)
    assert sampled_data == [Event(1, 100), Event(3, 200)]

    # Case 2: data changes at negedge of clock
    clock = [Event(0, 0), Event(1, 1), Event(2, 0), Event(3, 1), Event(4, 0), Event(5, 1)]
    data = [Event(0, 100), Event(2, 200), Event(4, 300)]
    sampled_data = sample_signal(clock, data)
    assert sampled_data == [Event(1, 100), Event(3, 200), Event(5, 300)]

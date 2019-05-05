from vcd import Event, Module, Signal
from typing import List, FrozenSet, Dict, Tuple, Iterator, Optional
import itertools
from dataclasses import dataclass


@dataclass(frozen=True)
class Property:
    a: FrozenSet[Signal]
    b: FrozenSet[Signal]


@dataclass(frozen=True)
class Alternating(Property):
    pass


@dataclass(frozen=True)
class PropertyStats:
    support: int
    falsifiable: bool
    falsified: bool


# Combine a and b delta traces into 1 delta trace which consists of tuples indicating
# whether a, b, or both occurred at a timestep
def zip_delta_traces(a: List[Event], b: List[Event]) -> Iterator[Tuple[Optional[Event], Optional[Event]]]:
    a_idx, b_idx = 0, 0
    while a_idx < len(a) or b_idx < len(b):
        # received an 'a' and 'b' on the same cycle
        if a_idx < len(a) and b_idx < len(b) and a[a_idx].time == b[b_idx].time:
            yield (a[a_idx], b[b_idx])
            a_idx = a_idx + 1
            b_idx = b_idx + 1
        # received a 'a' event
        elif (a_idx < len(a) and b_idx < len(b) and a[a_idx].time < b[b_idx].time) \
                or (b_idx == len(b) and a_idx < len(a)):
            yield (a[a_idx], None)
            a_idx = a_idx + 1
        # received a 'b' event
        elif a_idx < len(a) and b_idx < len(b) and a[a_idx].time > b[b_idx].time \
                or (a_idx == len(a) and b_idx < len(b)):
            yield (None, b[b_idx])
            b_idx = b_idx + 1
        else:
            assert False, "should not get here"


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


# This pattern is only really legitimate when used with boolean control signals
def mine_alternating(a: List[Event], b: List[Event]) -> PropertyStats:
    # If a == b, they have identical events, and although are strictly alternating, that
    # strict definition is useless for verification since a and b are identically sourced
    if a == b:
        return PropertyStats(support=0, falsifiable=True, falsified=True)
    automaton_state = 0
    falsifiable, support = False, 0
    for t in zip_delta_traces(a, b):
        # got a and b, no matter what state we are in, we move to the error state
        if t[0] is not None and t[1] is not None:
            return PropertyStats(support=support, falsifiable=True, falsified=True)
        elif t[0] is not None and t[1] is None:  # got a, but not b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:  # we already got an a before, so this pattern fails
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 1:
                automaton_state = 0
                support = support + 1  # a successful completion of the pattern
            elif automaton_state == 0:  # we haven't got an 'a' yet, so b shouldn't go first
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        else:
            assert False, "should not get here"
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine_next(a: List[Event], b: List[Event], clk_period: int) -> PropertyStats:
    automaton_state = 0
    falsifiable, support = False, 0
    a_event_time = 0
    for t in zip_delta_traces(a, b):
        if t[0] is not None and t[1] is not None:  # got a and b
            a_event_time = t[0].time
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                automaton_state = 1
                support = support + 1
        elif t[0] is not None and t[1] is None:  # got a, but not b
            a_event_time = t[0].time
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 1 and t[1].time == a_event_time + clk_period:
                automaton_state = 0
                support = support + 1
            elif automaton_state == 1 and t[1].time != a_event_time + clk_period:
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        else:
            assert False, "should not get here"
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine_evenutual(a: List[Event], b: List[Event]) -> PropertyStats:
    automaton_state = 0
    falsifiable, support = False, 0
    for t in zip_delta_traces(a, b):
        if t[0] is not None and t[1] is not None:  # got a and b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                support = support + 1  # TODO: is this the right idea?
                automaton_state = 2
            elif automaton_state == 2:
                automaton_state = 2
        elif t[0] is not None and t[1] is None:  # got a, but not b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                automaton_state = 1
            elif automaton_state == 2:
                automaton_state = 1
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 0:
                automaton_state = 0
            elif automaton_state == 1:
                automaton_state = 0
                support = support + 1
            elif automaton_state == 2:
                automaton_state = 0
                support = support + 1
        else:
            assert False, "should not get here"
    # This property can never be falsified, so the support is the primary indicator of usefulness
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine(module: Module, vcd_data: Dict[FrozenSet[Signal], List[Event]]):
    # Strip vcd_data so it only contains signals that are directly inside this module
    # and only mine permutations of signals directly inside a given module instance
    def signal_in_module(signal: str, module: str):
        last_dot = signal.rfind('.')
        signal_root = signal[0:last_dot]
        return signal_root == module

    vcd_data_scoped = {signal_set: trace for (signal_set, trace) in vcd_data.items()
                       if any([signal_in_module(s.name, module.name) for s in signal_set])}

    print("MODULE = {}".format(module.name))
    for combo in itertools.permutations(vcd_data_scoped.keys(), 2):
        combo_str = [[s.name for s in signal_set] for signal_set in combo]
        alternating_valid = mine_alternating(vcd_data_scoped[combo[0]], vcd_data_scoped[combo[1]])
        if alternating_valid.falsifiable and not alternating_valid.falsified:
            print("Alternating: {}, support {}".format(combo_str, alternating_valid.support))
        next_valid = mine_next(vcd_data_scoped[combo[0]], vcd_data_scoped[combo[1]], 2)
        if next_valid.falsifiable and not next_valid.falsified:
            print("Next: {}, support {}".format(combo_str, next_valid.support))
        eventual = mine_evenutual(vcd_data_scoped[combo[0]], vcd_data_scoped[combo[1]])
        if eventual.falsifiable and eventual.support > 0:
            print("Eventual: {}, support {}".format(combo_str, eventual.support))


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

    print("TESTING: mine_alternating")
    ma1 = mine_alternating(
        [Event(0, 1), Event(5, 0), Event(10, 1)],
        [Event(1, 0), Event(6, 1), Event(11, 0)]
    )
    assert ma1.falsifiable is True
    assert ma1.falsified is False

    print("TESTING: mine_next")
    mn1 = mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(4, 0), Event(8, 1)],
        2
    )
    assert mn1.falsifiable is True
    assert mn1.falsified is False

    mn2 = mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(8, 0)],
        2
    )
    assert mn2.falsifiable is True
    assert mn2.falsified is True

    print("TESTING: mine_eventual")
    me1 = mine_evenutual(
        [Event(2, 1), Event(20, 0)],
        [Event(2, 1)]
    )
    assert me1.support == 0
    assert me1.falsifiable is True

    me2 = mine_evenutual(
        [Event(2, 1), Event(20, 0)],
        [Event(4, 1), Event(6, 0), Event(30, 1)]
    )
    assert me2.falsifiable is True
    assert me2.support == 2

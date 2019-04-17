from vcd import Event
from typing import List


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
def mine_alternating(a: List[Event], b: List[Event]) -> bool:
    # If a == b, they have identical events, and although are strictly alternating, that
    # strict definition is useless for verification since a and b are identically sourced
    # TODO: check whether this is reasonable
    if a == b:
        return False
    automaton_state = 0
    a_idx, b_idx = 0, 0
    while a_idx < len(a) or b_idx < len(b):
        # received an 'a' and 'b' on the same cycle (don't advance the automaton)
        if a_idx < len(a) and b_idx < len(b) and a[a_idx].time == b[b_idx].time:
            a_idx = a_idx + 1
            b_idx = b_idx + 1
        # received an 'a' event
        elif (a_idx < len(a) and b_idx < len(b) and a[a_idx].time < b[b_idx].time) \
                or (b_idx == len(b) and a_idx < len(a)):
            if automaton_state == 0:
                automaton_state = 1
                a_idx = a_idx + 1
            else:
                return False
        # received an 'b' event
        elif a_idx < len(a) and b_idx < len(b) and a[a_idx].time > b[b_idx].time \
                or (a_idx == len(a) and b_idx < len(b)):
            if automaton_state == 1:
                automaton_state = 0
                b_idx = b_idx + 1
            else:
                return False
        else:
            print(a_idx, b_idx, automaton_state)
            assert False, "should not get here"
    return automaton_state == 0


def mine_next(a: List[Event], b: List[Event], clk_period: int) -> bool:
    automaton_state = 0
    patterns_seen = 0
    a_event_time = 0
    a_idx, b_idx = 0, 0
    while a_idx < len(a) or b_idx < len(b):
        # received an 'a' and 'b' on the same cycle
        if a_idx < len(a) and b_idx < len(b) and a[a_idx].time == b[b_idx].time:
            a_event_time = a[a_idx].time
            a_idx = a_idx + 1
            b_idx = b_idx + 1
            if automaton_state == 0: automaton_state = 1
        # received an 'a' event and NOT an 'b' event
        elif (a_idx < len(a) and b_idx < len(b) and a[a_idx].time < b[b_idx].time) \
                or (b_idx == len(b) and a_idx < len(a)):
            if automaton_state == 0: automaton_state = 1
            elif automaton_state == 1: return False  # didn't get a 'b' NEXT 'a'
            a_event_time = a[a_idx].time
            a_idx = a_idx + 1
        # received an 'b' event and NOT an 'a' event
        elif a_idx < len(a) and b_idx < len(b) and a[a_idx].time > b[b_idx].time \
                or (a_idx == len(a) and b_idx < len(b)):
            if automaton_state == 1 and b[b_idx].time == a_event_time + clk_period:
                automaton_state = 0
                b_idx = b_idx + 1
                patterns_seen = patterns_seen + 1
            elif automaton_state == 0:
                automaton_state = 0
                b_idx = b_idx + 1
            else:
                return False  # didn't get a 'b' NEXT 'a', but rather more than 1 clock
        else:
            print(a_idx, b_idx, automaton_state)
            assert False, "should not get here"
    return (automaton_state == 0 or automaton_state == 1) and patterns_seen > 0


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
    assert(mine_alternating(
        [Event(0, 1), Event(5, 0), Event(10, 1)],
        [Event(1, 0), Event(6, 1), Event(11, 0)]
    ))

    print("TESTING: mine_next")
    assert(mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(4, 0), Event(8, 1)],
        2
    ))
    assert(not mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(8, 0)],
        2
    ))

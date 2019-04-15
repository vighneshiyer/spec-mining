from vcd import Event
from typing import List


# TODO: don't mutate the lists and instead iterate over indices
def sample_signal(sampling_times: List[int], signal: List[Event]) -> List[Event]:
    """
    Samples a signal at the times given (typically immediately after the rising edge of a clock)
    Will throw an error if any sampling time is ambiguous
    :param sampling_times:
    :param signal:
    :return:
    """
    # Don't mutate the caller's lists
    sampling_times = sampling_times.copy()
    signal = signal.copy()
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


# This pattern is only really legitimate when used with boolean control signals
# TODO: mine_alternating should be false if a is a strict alias of b
def mine_alternating(a: List[Event], b: List[Event]) -> bool:
    automaton_state = 0
    a_idx, b_idx = 0, 0
    while a_idx < len(a) or b_idx < len(b):
        # received an 'a' and 'b' on the same cycle (this may be a violation)
        if a_idx < len(a) and b_idx < len(b) and a[a_idx].time == b[b_idx].time:
            a_idx = a_idx + 1
            b_idx = b_idx + 1
            #return False
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


if __name__ == "__main__":
    print("TESTING: sample_signal")
    # Case 1: data changes at same timestep as clock
    toy_clock = [Event(1 + x*5, int(x % 2 != 0)) for x in range(10)]
    toy_sampling_times = list(map(lambda x: x.time + 1, filter(lambda x: x.value == 1, toy_clock)))
    toy_data = [Event(2, 1), Event(18, 0)]
    print(toy_sampling_times)
    print(sample_signal(toy_sampling_times, toy_data))
    # TODO: Case 2: data changes at negedge of clock

    print("TESTING: mine_alternating")
    assert(mine_alternating([
        Event(0, 1), Event(5, 0), Event(10, 1)
    ], [
        Event(1, 0), Event(6, 1), Event(11, 0)
    ]))

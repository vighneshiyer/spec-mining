import sys
import itertools
from vcd import read_vcd, Signal
from analysis import sample_signal, mine_alternating, mine_next
import pprint
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('vcd_file', type=str, nargs=1)
    args = parser.parse_args()

    vcd_data = read_vcd(args.vcd_file[0])

    # TODO: Only pick out the top-level clock, this doesn't work for rocket-chip
    clock_names = {'clock', 'clk'}
    clocks = list(filter(
        lambda signal_set: any(['clk' in signal.name or 'clock' in signal.name for signal in signal_set]), vcd_data.keys()))
    assert len(clocks) == 1, "Found too many or no clocks. Got: {}".format(pprint.pformat(clocks))
    assert all([c.width == 1 for c in clocks[0]]), "All clock signals better have a width of 1"
    clock = clocks[0]
    print("Found clock {}".format(clock))

    # Sample signals on the clock
    vcd_data_sampled = {signal: sample_signal(vcd_data[clock], data) for (signal, data) in vcd_data.items()}
    # Remove the clock from the vcd data
    del vcd_data_sampled[clock]

    # Trim off events before the start_time commandline arg
    for signal, events in vcd_data_sampled.items():
        vcd_data_sampled[signal] = list(filter(lambda e: e.time > args.start_time, events))

    # Remove signals that should be ignored
    ignore_signals = {'_RAND', '_GEN', '_T', 'reset'}
    ignore_keys = []

    def ignore_sig(sig: Signal) -> bool:
        return any([ignore_str in sig.name for ignore_str in ignore_signals])

    for signal_set in vcd_data_sampled.keys():
        if all([ignore_sig(sig) for sig in signal_set]):
            ignore_keys.append(signal_set)

    for ignore_key in ignore_keys:
        del vcd_data_sampled[ignore_key]

    print("Found events for these signals:")
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint({", ".join(map(lambda s: s.name, signal)): len(data) for (signal, data) in vcd_data_sampled.items()})

    # Mine properties
    for combo in itertools.combinations(vcd_data_sampled.keys(), 2):
        # Only mine for small signals (like in the paper)
        if list(combo[0])[0].width > 4 or list(combo[1])[0].width > 4:
            continue
        combo_str = [[s.name for s in signal_set] for signal_set in combo]
        alternating_valid = mine_alternating(vcd_data_sampled[combo[0]], vcd_data_sampled[combo[1]])
        if alternating_valid:
            print("Alternating: {}".format(combo_str))
        next_valid = mine_next(vcd_data_sampled[combo[0]], vcd_data_sampled[combo[1]], 2)
        if next_valid:
            print("Next: {}".format(combo_str))

from vcd import read_vcd, Signal
from analysis import sample_signal, mine, Property
import pprint
import argparse
import pickle
from typing import List, FrozenSet, Dict, Set


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('--signal-bit-limit', type=int, default=5)
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('vcd_file', type=str, nargs=1)
    args = parser.parse_args()
    print("Miner called with arguments: {}".format(args))

    module_tree, vcd_data = read_vcd(args.vcd_file[0])

    # TODO: Only pick out the top-level clock, this doesn't work for rocket-chip
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
                        if len(trace) > 0 and list(signal_set)[0].width <= args.signal_bit_limit}

    print("Found events for these signals:")
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint({", ".join(map(lambda s: s.name, signal)): len(data) for (signal, data) in vcd_data_cleaned.items()})

    # Walk the module tree with DFS (iterative preorder traversal)
    module_queue = [module_tree]
    mined_properties = set()  # type: Set[Property]
    while len(module_queue) > 0:
        module = module_queue.pop()
        mined_properties.update(mine(module, vcd_data_cleaned))
        module_queue.extend(module.children)

    mined_properties = set(filter(lambda prop: prop.stats.support > 0, mined_properties))

    for property in mined_properties:
        if property.stats.falsified is False and property.stats.support > 100:
            print(property)

    if args.dump_file is not None:
        with open(args.dump_file, "wb") as f:
            pickle.dump(mined_properties, f)

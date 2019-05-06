import sys
from typing import Tuple, List
from analysis import Property, MinerResult, Eventual, PropertyStats
from vcd import VCDData, read_vcd_clean
import argparse
import pickle


# Check whether property p isn't violated after traces a and b have been extracted from it
# True if no violation, False if falsified
def check(p: Property, vcd_data: VCDData) -> Tuple[bool, int]:
    if p.a in vcd_data.keys() and p.b in vcd_data.keys():
        # Special case eventual since it can't be falsified but can lack support
        # TODO: figure out how to properly merge eventual properties
        if p.__class__ == Eventual:
            return True, 0
            #stats = p.mine(vcd_data[p.a], vcd_data[p.b])
            #return stats.support > 0, stats.falsified_time
        else:
            stats = p.mine(vcd_data[p.a], vcd_data[p.b])
            return not stats.falsified, stats.falsified_time
    else:
        return True, 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('--signal-bit-limit', type=int, default=5)
    parser.add_argument('vcd_file', type=str, nargs=1)
    parser.add_argument('prop_file', type=str, nargs=1)
    args = parser.parse_args()
    print("Checker called with arguments: {}".format(args))

    module_tree, vcd_data = read_vcd_clean(args.vcd_file[0], args.start_time, args.signal_bit_limit)
    violated_props = []  # type: List[Tuple[Property, PropertyStats, int]]
    with open(args.prop_file[0], 'rb') as prop_f:
        props = pickle.load(prop_f)  # type: MinerResult
        for (prop, stats) in props.items():
            if stats.falsified is False:
                not_violated, falsified_time = check(prop, vcd_data)
                if not not_violated:
                    violated_props.append((prop, stats, falsified_time))

    violated_props_sorted = sorted(violated_props, key=lambda x: x[2])
    for (prop, stats, falsified_time) in violated_props_sorted:
        print("ERROR on property {} with support {} at time {}".format(prop, stats.support, falsified_time))

    if len(violated_props) > 0:
        sys.exit(1)

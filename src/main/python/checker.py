import sys
from analysis import Property
from vcd import VCDData, read_vcd_clean
import argparse
import pickle


# Check whether property p isn't violated after traces a and b have been extracted from it
# True if no violation, False if falsified
def check(p: Property, vcd_data: VCDData) -> bool:
    if p.stats.falsified:
        return True
    else:
        if p.a in vcd_data.keys() and p.b in vcd_data.keys():
            stats = p.mine(vcd_data[p.a], vcd_data[p.b])
            print(stats)
            return not stats.falsified
        else:
            return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('--signal-bit-limit', type=int, default=5)
    parser.add_argument('vcd_file', type=str, nargs=1)
    parser.add_argument('prop_file', type=str, nargs=1)
    args = parser.parse_args()
    print("Checker called with arguments: {}".format(args))

    module_tree, vcd_data = read_vcd_clean(args.vcd_file[0], args.start_time, args.signal_bit_limit)
    good = True
    with open(args.prop_file[0], 'rb') as prop_f:
        props = pickle.load(prop_f)
        for p in props:
            if not check(p, vcd_data):
                print("ERROR on property {}".format(p))
                good = False
    if not good:
        sys.exit(1)

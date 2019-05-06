from vcd import read_vcd_clean
from analysis import mine_modules_recurse
import argparse
import pickle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('--signal-bit-limit', type=int, default=5)
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('vcd_file', type=str, nargs=1)
    args = parser.parse_args()
    print("Miner called with arguments: {}".format(args))

    module_tree, vcd_data = read_vcd_clean(args.vcd_file[0], args.start_time, args.signal_bit_limit)
    props = mine_modules_recurse(module_tree, vcd_data)
    print("Top 10 properties:")
    sorted_props = sorted(props.items(), key=lambda x: x[1].support, reverse=True)[:30]
    for (prop, stats) in sorted_props:
        print("{}, support: {}".format(prop, stats.support))

    if args.dump_file is not None:
        with open(args.dump_file, "wb") as f:
            pickle.dump(props, f)



# Analyze riscv-mini via spec mining and combining
import sys
import os
from vcd import read_vcd_clean
from miner import mine_modules_recurse
from merger import merge_props
from joblib import Parallel, delayed
from checker import check
import argparse
import pickle

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('--riscv-mini-root', type=str)
    args = parser.parse_args()
    print("riscv-mini analysis called with arguments: {}".format(args))

    vcd_root = args.riscv_mini_root + "/outputs/"
    vcd_files = list(filter(lambda f: 'vcd' in f and 'rv32ui-p-' in f, os.listdir(vcd_root)))
    start_time = 12
    bit_limit = 4

    vcd_data = [read_vcd_clean(vcd_root + vcd, start_time, bit_limit) for vcd in vcd_files]
    props = Parallel(n_jobs=4)(delayed(mine_modules_recurse)(module, data) for (module, data) in vcd_data)

    print("Merging mined properties")
    merged_props = merge_props(props)

    # After everything's been merged, strip away properties that have been falsified
    stripped_props = {prop: stats for (prop, stats) in merged_props.items()
                      if stats.falsifiable and not stats.falsified and stats.support > 0}
    # Sort from highest to lowest support
    sorted_props = sorted(stripped_props.items(), key=lambda x: x[1].support, reverse=True)[:30]
    print("Top 30 properties")
    for (prop, stats) in sorted_props:
        print("{}, support: {}".format(prop, stats.support))

    print("Checking mined properties against golden traces")
    good = True
    for (module, data) in vcd_data:
        for p in stripped_props.keys():
            if not check(p, data):
                good = False
                print("ERROR on property {}".format(p))
    if not good:
        sys.exit(1)

    if args.dump_file is not None:
        with open(args.dump_file, 'wb') as f:
            pickle.dump(stripped_props, f)

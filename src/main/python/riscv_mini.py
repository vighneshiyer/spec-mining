# Analyze riscv-mini via spec mining and combining
import os
from vcd import read_vcd_clean
from analysis import Property
from miner import mine_from_vcd
from merger import merge_props
from typing import List, Set
from joblib import Parallel, delayed
from checker import check

if __name__ == "__main__":
    VCD_ROOT = '/home/vighnesh/20-research/24-repos/riscv-mini/outputs/'
    vcd_files = list(filter(lambda f: 'vcd' in f and 'rv32ui-p-' in f, os.listdir(VCD_ROOT)))[:2]
    start_time = 12
    bit_limit = 4

    props = Parallel(n_jobs=4)(delayed(mine_from_vcd)(VCD_ROOT + vcd, start_time, bit_limit) for vcd in vcd_files)

    print("Merging mined properties")
    merged_props = merge_props(props)

    # After everything's been merged, strip away properties that have been falsified
    stripped_props = {k:v for (k,v) in merged_props.items() if v.falsifiable and not v.falsified and v.support > 0}
    # Sort from highest to lowest support
    sorted_props = sorted(stripped_props.items(), key=lambda x: x[1].support, reverse=True)
    print(len(sorted_props))
    for (p, s) in sorted_props[:10]:
        print(p.__class__.__name__, p.a, p.b, s.support)

    print("Checking mined properties against golden traces")
    for vcd in vcd_files:
        module_tree, vcd_data = read_vcd_clean(VCD_ROOT + vcd, start_time, bit_limit)
        for p in stripped_props.keys():
            if not check(p, vcd_data):
                print("ERROR on property {} on vcd file {}".format(p, vcd))

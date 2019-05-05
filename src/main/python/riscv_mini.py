# Analyze riscv-mini via spec mining and combining
import os
from analysis import Property
from miner import mine_from_vcd
from merger import merge_props
from typing import List, Set

if __name__ == "__main__":
    VCD_ROOT = '/home/vighnesh/20-research/24-repos/riscv-mini/outputs/'
    vcd_files = list(filter(lambda f: 'vcd' in f and 'rv32ui-p-' in f, os.listdir(VCD_ROOT)))
    props = []  # type: List[Set[Property]]

    for vcd in vcd_files[:2]:
        print("Mining from file {}".format(vcd))
        props.append(mine_from_vcd(VCD_ROOT + vcd, 12, 4))

    merged_props = merge_props(props)
    #for (p, s) in merged_props.items():
        #if not s.falsified and s.support > 0:
            #print(p.__class__.__name__, p.a, p.b, s.support)

    # After everything's been merged, strip away properties that have been falsified
    stripped_props = {k:v for (k,v) in merged_props.items() if not v.falsified and v.support > 0}
    sorted_props = sorted(stripped_props.items(), key=lambda x: x[1].support, reverse=True)
    for (p, s) in sorted_props[:100]:
        print(p.__class__.__name__, p.a, p.b, s.support)

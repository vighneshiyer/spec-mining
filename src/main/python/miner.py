from vcd import read_vcd_clean, Signal
from analysis import mine, Property
import pprint
import argparse
import pickle
from typing import Set


def mine_from_vcd(vcd_file_path: str, start_time: int, signal_bit_limit: int) -> Set[Property]:
    print("Mining from VCD: {}".format(vcd_file_path))
    module_tree, vcd_data = read_vcd_clean(vcd_file_path, start_time, signal_bit_limit)
    #print("Found events for these signals:")
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint({", ".join(map(lambda s: s.name, signal)): len(data) for (signal, data) in vcd_data.items()})

    # Walk the module tree with DFS (iterative preorder traversal)
    module_queue = [module_tree]
    mined_properties = set()  # type: Set[Property]
    while len(module_queue) > 0:
        module = module_queue.pop()
        mined_properties.update(mine(module, vcd_data))
        module_queue.extend(module.children)

    #mined_properties = set(filter(lambda p: p.stats.support > 0, mined_properties))
    return mined_properties


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-time', type=int, default=0)
    parser.add_argument('--signal-bit-limit', type=int, default=5)
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('vcd_file', type=str, nargs=1)
    args = parser.parse_args()
    print("Miner called with arguments: {}".format(args))

    props = mine_from_vcd(args.vcd_file[0], args.start_time, args.signal_bit_limit)
    for prop in props:
        if prop.stats.falsified is False and prop.stats.support > 100:
            print(prop)

    if args.dump_file is not None:
        with open(args.dump_file, "wb") as f:
            pickle.dump(props, f)



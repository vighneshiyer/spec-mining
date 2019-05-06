import argparse
import pickle
from typing import List
from analysis import PropertyStats, MinerResult


def merge_props(props: List[MinerResult]) -> MinerResult:
    merged_props = {}  # type: MinerResult
    for propset in props:
        for (new_prop, new_stats) in propset.items():
            if new_prop not in merged_props:
                merged_props[new_prop] = new_stats
            # If prop is found it means a, b, and the property type match
            else:
                old_prop_stats = merged_props[new_prop]
                if new_stats.falsified:
                    merged_props[new_prop] = \
                        PropertyStats(support=old_prop_stats.support, falsifiable=True, falsified=True)
                else:
                    merged_props[new_prop] = \
                        PropertyStats(support=old_prop_stats.support+new_stats.support,
                                      falsifiable=True, falsified=old_prop_stats.falsified)
    return merged_props


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('property_dump', type=str, nargs='+')
    args = parser.parse_args()
    print("Merger called with arguments: {}".format(args))

    prop_list = []  # type: List[MinerResult]
    for prop_file in args.property_dump:
        with open(prop_file, 'rb') as f:
            prop_list.append(pickle.load(f))

    aggregate_props = merge_props(prop_list)

    if args.dump_file is not None:
        with open(args.dump_file, 'wb') as f:
            pickle.dump(aggregate_props, f)

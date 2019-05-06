import argparse
import pickle
from typing import Set, Dict, List
from analysis import Property, PropertyStats


def merge_props(props: List[Set[Property]]) -> Dict[Property, PropertyStats]:
    merged_props = {}  # type: Dict[Property, PropertyStats]

    for propset in props:
        for new_prop in propset:
            if new_prop not in merged_props:
                merged_props[new_prop] = new_prop.stats
            # If prop is found it means a, b, and the property type match
            else:
                old_prop = merged_props[new_prop]
                if new_prop.stats.falsified:
                    print("FALSIFIED PROPERTY {}".format(new_prop))
                    merged_props[new_prop] = \
                        PropertyStats(support=old_prop.support, falsifiable=True, falsified=True)
                else:
                    merged_props[new_prop] = \
                        PropertyStats(support=old_prop.support+new_prop.stats.support,
                                      falsifiable=True, falsified=old_prop.falsified)

    return merged_props


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dump-file', type=str)
    parser.add_argument('property_dump', type=str, nargs='+')
    args = parser.parse_args()
    print("Merger called with arguments: {}".format(args))

    prop_list = []  # type: List[Set[Property]]
    for prop_file in args.property_dump:
        with open(prop_file, 'rb') as f:
            prop_list.append(pickle.load(f))

    aggregate_props = merge_props(prop_list)
    #for (p, s) in aggregate_props.items():
        #if not s.falsified and s.support > 0:
            #print(p)

    with open(args.dump_file, 'wb') as f:
        pickle.dump(aggregate_props, f)

import sys
import itertools
from typing import List
from vcd import read_vcd, Event, Signal
from analysis import sample_signal, mine_alternating


if __name__ == "__main__":
    ignore_signals = {'_RAND', '_GEN', '_T', 'reset'}
    vcd_data = read_vcd(sys.argv[1], ignore_signals)

    # Only sample signals at rising edge of the clock
    # TODO: Only pick out the top-level clock
    clock_names = {'clock', 'clk'}
    clocks = list(filter(lambda x: any([name in x.name for name in clock_names]), vcd_data.keys()))
    assert len(clocks) == 1, "Found too many or no clocks. Got: {}".format(clocks)
    assert clocks[0].width == 1
    clock = clocks[0]
    print("Found clock {}".format(clock))

    # Scale up the event times because the verilator VCD has a clock with 2ns period
    # and that isn't enough resolution to construct posedge times that are nudged a bit
    for signal, events in vcd_data.items():
        vcd_data[signal] = list(map(lambda e: Event(e.time*10, e.value), events))

    # Take all the rising clock edges and nudge them forward by 1 timestep as the signal sampling point
    clock_posedges = list(map(lambda x: x.time - 1, filter(lambda x: x.value == 1, vcd_data[clock])))

    # Sample signals on the clock
    vcd_data_sampled = {signal: sample_signal(clock_posedges, data) for (signal, data) in vcd_data.items()}
    # Remove the clock from the vcd data
    del vcd_data_sampled[clock]
    print("Found events for these signals:")
    print({signal.name: len(data) for (signal, data) in vcd_data_sampled.items()})

    # Only consider steady state behavior
    for signal, events in vcd_data_sampled.items():
        vcd_data_sampled[signal] = list(filter(lambda e: e.time > 1000, events))

    # Mine: a A a, a alternates with b where a and b are delta events
    for combo in itertools.combinations(vcd_data_sampled.keys(), 2):
        alternating_valid = mine_alternating(vcd_data_sampled[combo[0]], vcd_data_sampled[combo[1]])
        if alternating_valid:
            combo_str = [x.name for x in combo]
            print("Alternating: {}".format(combo_str))

from vcd import Event, Module, Signal, VCDData, DeltaTrace
from typing import List, FrozenSet, Dict, Tuple, Iterator, Optional, Set, Callable
import itertools
from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyStats:
    support: int
    falsifiable: bool
    falsified: bool


@dataclass(frozen=True, eq=False)
class Property:
    a: FrozenSet[Signal]
    b: FrozenSet[Signal]
    # TODO: these classes should be split
    stats: PropertyStats

    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats:
        pass

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Alternating(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_alternating(a, b)
    def __repr__(self) -> str:
        return "Alternating {} -> {}, support = {}".format(self.a, self.b, self.stats.support)
    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b
    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Next(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_next(a, b)
    def __repr__(self) -> str:
        return "Next {} -> {}, support = {}".format(self.a, self.b, self.stats.support)
    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b
    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Until(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_until(a, b)
    def __repr__(self) -> str:
        return "Until {} -> {}, support = {}".format(self.a, self.b, self.stats.support)
    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b
    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Eventual(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_evenutual(a, b)
    def __repr__(self) -> str:
        return "Eventual {} -> {}, support = {}".format(self.a, self.b, self.stats.support)
    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b
    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


# Combine a and b delta traces into 1 delta trace which consists of tuples indicating
# whether a, b, or both occurred at a timestep
def zip_delta_traces(a: List[Event], b: List[Event]) -> Iterator[Tuple[Optional[Event], Optional[Event]]]:
    a_idx, b_idx = 0, 0
    while a_idx < len(a) or b_idx < len(b):
        # received an 'a' and 'b' on the same cycle
        if a_idx < len(a) and b_idx < len(b) and a[a_idx].time == b[b_idx].time:
            yield (a[a_idx], b[b_idx])
            a_idx = a_idx + 1
            b_idx = b_idx + 1
        # received a 'a' event
        elif (a_idx < len(a) and b_idx < len(b) and a[a_idx].time < b[b_idx].time) \
                or (b_idx == len(b) and a_idx < len(a)):
            yield (a[a_idx], None)
            a_idx = a_idx + 1
        # received a 'b' event
        elif a_idx < len(a) and b_idx < len(b) and a[a_idx].time > b[b_idx].time \
                or (a_idx == len(a) and b_idx < len(b)):
            yield (None, b[b_idx])
            b_idx = b_idx + 1
        else:
            assert False, "should not get here"


# This pattern is only really legitimate when used with boolean control signals
def mine_alternating(a: List[Event], b: List[Event]) -> PropertyStats:
    # If a == b, they have identical events, and although are strictly alternating, that
    # strict definition is useless for verification since a and b are identically sourced
    if a == b:
        return PropertyStats(support=0, falsifiable=True, falsified=True)
    automaton_state = 0
    falsifiable, support = False, 0
    for t in zip_delta_traces(a, b):
        # got a and b, no matter what state we are in, we move to the error state
        if t[0] is not None and t[1] is not None:
            return PropertyStats(support=support, falsifiable=True, falsified=True)
        elif t[0] is not None and t[1] is None:  # got a, but not b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:  # we already got an a before, so this pattern fails
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 1:
                automaton_state = 0
                support = support + 1  # a successful completion of the pattern
            elif automaton_state == 0:  # we haven't got an 'a' yet, so b shouldn't go first
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        else:
            assert False, "should not get here"
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine_next(a: List[Event], b: List[Event], clk_period: int = 2) -> PropertyStats:
    automaton_state = 0
    falsifiable, support = False, 0
    a_event_time = 0
    for t in zip_delta_traces(a, b):
        if t[0] is not None and t[1] is not None:  # got a and b
            a_event_time = t[0].time
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                automaton_state = 1
                support = support + 1
        elif t[0] is not None and t[1] is None:  # got a, but not b
            a_event_time = t[0].time
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 1 and t[1].time == a_event_time + clk_period:
                automaton_state = 0
                support = support + 1
            elif automaton_state == 1 and t[1].time != a_event_time + clk_period:
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        else:
            assert False, "should not get here"
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine_evenutual(a: List[Event], b: List[Event]) -> PropertyStats:
    automaton_state = 0
    falsifiable, support = False, 0
    for t in zip_delta_traces(a, b):
        if t[0] is not None and t[1] is not None:  # got a and b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                support = support + 1  # TODO: is this the right idea?
                automaton_state = 2
            elif automaton_state == 2:
                automaton_state = 2
        elif t[0] is not None and t[1] is None:  # got a, but not b
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                automaton_state = 1
            elif automaton_state == 2:
                automaton_state = 1
        elif t[0] is None and t[1] is not None:  # got b, but not a
            if automaton_state == 0:
                automaton_state = 0
            elif automaton_state == 1:
                automaton_state = 0
                support = support + 1
            elif automaton_state == 2:
                automaton_state = 0
                support = support + 1
        else:
            assert False, "should not get here"
    # This property can never be falsified, so the support is the primary indicator of usefulness
    # TODO: using falsifiable as hack to strip away eventual properties with no support
    return PropertyStats(support=support, falsifiable=support > 0, falsified=False)


def mine_until(a: List[Event], b: List[Event]) -> PropertyStats:
    automaton_state = 0
    falsifiable, support = False, 0
    for t in zip_delta_traces(a, b):
        if t[0] is not None and t[1] is not None:
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            elif automaton_state == 1:
                automaton_state = 1
                support = support + 1
        elif t[0] is not None and t[1] is None:
            if automaton_state == 0:
                automaton_state = 1
                falsifiable = True
            # In state == 1, we have already seen delta a and if we see another delta a without also a delta b,
            # then a didn't remain stable until b toggled
            elif automaton_state == 1:
                return PropertyStats(support=support, falsifiable=falsifiable, falsified=True)
        elif t[0] is None and t[1] is not None:
            if automaton_state == 0:
                automaton_state = 0
            elif automaton_state == 1:
                automaton_state = 0
                support = support + 1
        else:
            assert False, "should not get here"
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine(module: Module, vcd_data: Dict[FrozenSet[Signal], List[Event]]) -> Set[Property]:
    # Strip vcd_data so it only contains signals that are directly inside this module
    # and only mine permutations of signals directly inside a given module instance
    def signal_in_module(signal: str, module: str):
        last_dot = signal.rfind('.')
        signal_root = signal[0:last_dot]
        return signal_root == module

    vcd_data_scoped = {signal_set: trace for (signal_set, trace) in vcd_data.items()
                       if any([signal_in_module(s.name, module.name) for s in signal_set])}

    ret_set = set()
    miners = [mine_alternating, mine_next, mine_evenutual, mine_until]  # type: List[Callable[[List[Event], List[Event]], PropertyStats]]
    property_classes = [Alternating, Next, Eventual, Until]
    print("Mining module = {}".format(module.name))
    for combo in itertools.permutations(vcd_data_scoped.keys(), 2):
        for (miner, property_class) in zip(miners, property_classes):
            pattern_stats = miner(vcd_data_scoped[combo[0]], vcd_data_scoped[combo[1]])
            if pattern_stats.falsifiable:
                ret_set.add(property_class(frozenset(combo[0]), frozenset(combo[1]), pattern_stats))
    return ret_set


if __name__ == "__main__":
    print("TESTING: mine_alternating")
    ma1 = mine_alternating(
        [Event(0, 1), Event(5, 0), Event(10, 1)],
        [Event(1, 0), Event(6, 1), Event(11, 0)]
    )
    assert ma1.falsifiable is True
    assert ma1.falsified is False

    print("TESTING: mine_next")
    mn1 = mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(4, 0), Event(8, 1)],
        2
    )
    assert mn1.falsifiable is True
    assert mn1.falsified is False

    mn2 = mine_next(
        [Event(2, 1), Event(6, 0)],
        [Event(8, 0)],
        2
    )
    assert mn2.falsifiable is True
    assert mn2.falsified is True

    print("TESTING: mine_eventual")
    me1 = mine_evenutual(
        [Event(2, 1), Event(20, 0)],
        [Event(2, 1)]
    )
    assert me1.support == 0
    assert me1.falsifiable is True

    me2 = mine_evenutual(
        [Event(2, 1), Event(20, 0)],
        [Event(4, 1), Event(6, 0), Event(30, 1)]
    )
    assert me2.falsifiable is True
    assert me2.support == 2

    print("TESTING: mine_until")
    mu1 = mine_until(
        [Event(2, 1), Event(20, 0)],
        [Event(6, 0), Event(22, 1)]
    )
    assert mu1.falsifiable is True
    assert mu1.falsified is False
    assert mu1.support == 2

    mu2 = mine_until(
        [Event(2, 1), Event(6, 0), Event(20, 1)],
        [Event(0, 1), Event(8, 0)]
    )
    assert mu2.falsifiable is True
    assert mu2.falsified is True

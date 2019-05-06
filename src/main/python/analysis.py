from vcd import Event, Module, VCDData, DeltaTrace, AliasedSignals
from typing import Dict, Tuple, Iterator, Optional
import itertools
from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyStats:
    support: int
    falsifiable: bool
    falsified: bool


@dataclass(frozen=True, eq=False)
class Property:
    a: AliasedSignals
    b: AliasedSignals

    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats:
        pass

    def clean_set(self, x: AliasedSignals) -> str:
        return list(x)[0].name

    def __repr__(self) -> str:
        return "{} {} -> {}".format(self.__class__.__name__, self.clean_set(self.a), self.clean_set(self.b))

    def __str__(self) -> str:
        return "{} {} -> {}".format(self.__class__.__name__, self.clean_set(self.a), self.clean_set(self.b))

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Alternating(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_alternating(a, b)

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Next(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_next(a, b)

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Until(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_until(a, b)

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


@dataclass(frozen=True, eq=False)
class Eventual(Property):
    def mine(self, a: DeltaTrace, b: DeltaTrace) -> PropertyStats: return mine_evenutual(a, b)

    def __eq__(self, other) -> bool:
        return self.__class__.__name__ == other.__class__.__name__ and \
               self.a == other.a and \
               self.b == other.b

    def __hash__(self) -> int:
        return self.__class__.__name__.__hash__() + self.a.__hash__() + self.b.__hash__()


MinerResult = Dict[Property, PropertyStats]


# Combine a and b delta traces into 1 delta trace which consists of tuples indicating
# whether a, b, or both occurred at a timestep
def zip_delta_traces(a: DeltaTrace, b: DeltaTrace) -> Iterator[Tuple[Optional[Event], Optional[Event]]]:
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
def mine_alternating(a: DeltaTrace, b: DeltaTrace) -> PropertyStats:
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


def mine_next(a: DeltaTrace, b: DeltaTrace, clk_period: int = 2) -> PropertyStats:
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


def mine_evenutual(a: DeltaTrace, b: DeltaTrace) -> PropertyStats:
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
    return PropertyStats(support=support, falsifiable=falsifiable, falsified=False)


def mine_until(a: DeltaTrace, b: DeltaTrace) -> PropertyStats:
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


def mine_module(module: Module, vcd_data: VCDData) -> MinerResult:
    # Strip vcd_data so it only contains signals that are directly inside this module
    # and only mine permutations of signals directly inside a given module instance
    def signal_in_module(signal: str, module: str):
        last_dot = signal.rfind('.')
        signal_root = signal[0:last_dot]
        return signal_root == module

    vcd_data_scoped = {signal_set: trace for (signal_set, trace) in vcd_data.items()
                       if any([signal_in_module(s.name, module.name) for s in signal_set])}

    result = {}  # type: MinerResult
    property_classes = [Alternating, Next, Eventual, Until]
    print("Mining module = {}".format(module.name))
    for combo in itertools.permutations(vcd_data_scoped.keys(), 2):
        for prop_type in property_classes:
            a = vcd_data_scoped[combo[0]]
            b = vcd_data_scoped[combo[1]]
            prop = prop_type(combo[0], combo[1])
            pattern_stats = prop.mine(a, b)
            if pattern_stats.falsifiable:
                result[prop] = pattern_stats
    return result


def mine_modules_recurse(module: Module, vcd_data: VCDData) -> MinerResult:
    # Walk the module tree with DFS (iterative preorder traversal)
    module_queue = [module]
    result = {}  # type: MinerResult
    while len(module_queue) > 0:
        module = module_queue.pop()
        module_mine = mine_module(module, vcd_data)
        for (k, v) in module_mine.items():
            result[k] = v
        module_queue.extend(module.children)
    return result


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

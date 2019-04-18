Specification Mining for Bug Localization
=========================================

Forked from `freechipsproject/chisel-template`. Implements a spec mining engine (VCD to mined LTL properties).

# Quickstart
Run this:
```bash
sbt test
cd src/main/python
python main.py --start-time 1000 --signal-bit-limit 32 ../../../vcd/gcd/GCD.vcd
python main.py --start-time 10 ../../../vcd/life/Life.vcd
python main.py --start-time 0 --signal-bit-width 32 ../../../vcd/risc/Risc.vcd
```

Results:
```
Alternating: [['TOP.io_isWr', 'TOP.Risc.io_isWr'], ['TOP.Risc.code_inst_data']]
Alternating: [['TOP.io_isWr', 'TOP.Risc.io_isWr'], ['TOP.Risc.op']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.op']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.ra']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.rb']]
Alternating: [['TOP.Risc.rci'], ['TOP.Risc.rai']]
Next: [['TOP.Risc.rai'], ['TOP.Risc.ra']]
Next: [['TOP.Risc.rai'], ['TOP.Risc.rb']]
Alternating: [['TOP.Risc.op'], ['TOP.Risc.ra']]
Alternating: [['TOP.Risc.op'], ['TOP.Risc.rb']]
```

This shows that the signal `TOP.Risc.io_isWr` alternates delta events with `Top.Risc.code_inst_data` in the `Riscv.vcd` trace VCD.
There may be multiple signals in the VCD which are aliased to the same logical signal and that is represented as a list of aliased signals.

You can pass `--start-time n` to skip forward `n` clocks on each signal trace before trying to mine any properties.
This allows us to exclude *potentially* weird pre-reset behavior if desired.

You can pass `--signal-bit-width n` to strip signals with bitwidth greater than n from consideration when mining LTL properties.
This can be used to exclude datapath signals (for a microprocessor) whose delta events are irrelevant when mining for control properties.
The default value is 5 (from Wenchao Li's DAC 2010 paper).

# Mining on riscv-mini
We're going to mine properties from traces of execution of [riscv-mini](https://github.com/ucb-bar/riscv-mini), a simple 3-stage pipelined in-order RISC-V core with L1 caches.
To generate a bunch of sample VCD files from `riscv-mini` run:

```bash
git clone git@github.com:ucb-bar/riscv-mini
cd riscv-mini
make
make verilator
make run-tests
```

Now invoke the property miner on those VCD files:

```bash
cd src/main/python
python main.py --start-time 10 --signal-bit-width 5 /path/to/riscv-mini/outputs/rv32ui-p-sw.vcd
```

# TODO
- Prof. Seshia's Advice (from mini-update 1):
    - Try to get this working on a complex design (like riscv-mini) right away and see if the existing templates work out when introducing a bug which only impacts the execution trace a bit after the actual bug impacts the design (like a prefetcher bug which only manifests in a high-level property failure after the program fetches the bad data)
    - Then you can figure out if the spec mining engine fails, what needs work: is it the limitation of the templates in mining interesting properties, or is this methodology not tenable in the first place


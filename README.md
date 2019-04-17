Specification Mining for Bug Localization
=========================================

Forked from `freechipsproject/chisel-template`. Implements a spec mining engine (VCD to mined LTL properties).

# Quickstart
Run this:
```bash
sbt test
cd src/main/python
python main.py --start-time 0 ../../../vcd/risc/Risc.vcd
```

Results:
```
Alternating: [['TOP.Risc.io_isWr', 'TOP.io_isWr', 'TOP.Risc.code__T_4_en'], ['TOP.Risc.code_inst_data']]
Alternating: [['TOP.Risc.io_isWr', 'TOP.io_isWr', 'TOP.Risc.code__T_4_en'], ['TOP.Risc.op']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.op']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.ra']]
Alternating: [['TOP.Risc.code_inst_data'], ['TOP.Risc.rb']]
Alternating: [['TOP.Risc.rci', 'TOP.Risc.file__T_12_addr'], ['TOP.Risc.rai', 'TOP.Risc.file__T_1_addr']]
Alternating: [['TOP.Risc.op'], ['TOP.Risc.ra']]
Alternating: [['TOP.Risc.op'], ['TOP.Risc.rb']]
```
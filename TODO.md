- [ ] Get GCD test running with more test vectors and more randomness in input injection and output extraction from R/V interface
- [ ] Develop an even simpler DUT with R/V interfaces and deterministic delay
- [ ] vcd.py currently uses hardcoded `clock_symbol` and `reset_symbol` but that should be derived from scanning the `clock` and `reset` nets from the top-level

- Sanjit's Advice:
    - Try to get this working on a complex design (like riscv-mini) right away and see if the existing templates work out when introducing a bug which only impacts the execution trace a bit after the actual bug impacts the design (like a prefetcher bug which only manifests in a high-level property failure after the program fetches the bad data)
    - Then you can figure out if the spec mining engine fails, what needs work: is it the limitation of the templates in mining interesting properties, or is this methodology not tenable in the first place
    - We need to get this working at a base level very quickly

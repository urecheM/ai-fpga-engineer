# FPGA engineering notes (offline KB seed)

## Raising the maximum clock frequency (Fmax)
Register the critical path: inserting a pipeline register splits a long
combinational path into two shorter register-to-register paths, trading one
clock of latency for higher Fmax. Measure before and after with place-and-route
(nextpnr reports achieved Fmax); estimates only rank options.

## Resets on FPGAs
Prefer synchronous, active-high resets on Xilinx/Lattice fabrics: they map
directly onto the flip-flop's synchronous set/reset and avoid recovery/removal
timing on an asynchronous net. Every architectural state register needs a
defined power-up or reset value.

## Avoiding inferred latches
A combinational process must assign its outputs on every path: give every
`case` a `when others` and every `if` an `else` (or a default assignment at the
top). An unassigned path infers a level-sensitive latch, which breaks timing
analysis and is almost never intended.

## Area reduction by resource sharing
Two arithmetic operators that are never active simultaneously can share one
unit: a - b = a + not(b) + 1 lets ADD and SUB share a single adder, saving one
adder of LUTs for a mux's worth of overhead. Verify the shared path separately;
it is a classic source of borrow-polarity bugs.

## Trusting numbers
Pre-synthesis estimates are ranking aids. Cell counts come from synthesis
(yosys `stat`), timing from place-and-route (nextpnr report), and the final
authority is the device: sweep the PLL upward on hardware until failure and
compare against the reported Fmax.

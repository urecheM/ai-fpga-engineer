-- Self-checking testbench for uart_tx (8N1, one clock per bit via tick='1').
-- Drives a byte and verifies the serial frame: start(0), data LSB-first, stop(1).
-- Pass => "ALL TESTS PASSED"; mismatch => severity failure (non-zero exit).
-- NOTE: outputs of uart_tx are registered, so tx updates one clock after the
-- state/tick condition; the checks below account for that latency.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity uart_tx_tb is
end entity uart_tx_tb;

architecture tb of uart_tx_tb is
  signal clk, rst, tick, start, tx, tx_busy : std_logic := '0';
  signal data : std_logic_vector(7 downto 0) := (others => '0');
  constant BYTE : std_logic_vector(7 downto 0) := "10110010";
begin
  dut : entity work.uart_tx
    port map (clk => clk, rst => rst, tick => tick, start => start,
              data => data, tx => tx, tx_busy => tx_busy);

  stim : process
    variable errors : natural := 0;
    variable expect : std_logic_vector(0 to 9);  -- start + 8 data + stop

    procedure tick_clk is
    begin
      clk <= '0'; wait for 5 ns;
      clk <= '1'; wait for 5 ns;
    end procedure;
  begin
    expect(0) := '0';                              -- start bit
    for i in 0 to 7 loop
      expect(i + 1) := BYTE(i);                     -- data, LSB first
    end loop;
    expect(9) := '1';                              -- stop bit

    tick <= '1';
    rst  <= '1';                 tick_clk;          -- reset -> IDLE
    rst  <= '0'; data <= BYTE; start <= '1'; tick_clk;  -- IDLE -> START (latch)
    start <= '0';                tick_clk;          -- START -> DATA, tx <= start bit

    if tx /= expect(0) then
      errors := errors + 1;
      report "start bit mismatch" severity error;
    end if;

    for i in 1 to 9 loop
      tick_clk;                                     -- each subsequent bit
      if tx /= expect(i) then
        errors := errors + 1;
        report "frame bit " & integer'image(i) & " mismatch" severity error;
      end if;
    end loop;

    if errors = 0 then
      report "ALL TESTS PASSED (uart_tx frame verified)" severity note;
    else
      report integer'image(errors) & " frame bit(s) FAILED" severity failure;
    end if;
    wait;
  end process;
end architecture tb;

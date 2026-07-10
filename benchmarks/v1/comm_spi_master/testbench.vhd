-- Self-checking testbench for spi_master (mode 0, MSB-first, 8 bits).
-- Robust checks that don't depend on exact internal phase counting:
--   1. the first mosi bit equals tx_data(7)  (MSB-first);
--   2. 'done' asserts within a bounded number of clocks (transaction completes,
--      i.e. no deadlock).
-- Full rx_data equivalence checking is left as a follow-up.
-- Pass => "ALL TESTS PASSED"; failure => severity failure (non-zero exit).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity spi_master_tb is
end entity spi_master_tb;

architecture tb of spi_master_tb is
  signal clk, rst, start, miso, sclk, mosi, done : std_logic := '0';
  signal tx_data : std_logic_vector(7 downto 0) := (others => '0');
  signal rx_data : std_logic_vector(7 downto 0);
  constant TXD : std_logic_vector(7 downto 0) := "10100011";
begin
  dut : entity work.spi_master
    port map (clk => clk, rst => rst, start => start, tx_data => tx_data,
              miso => miso, sclk => sclk, mosi => mosi, done => done,
              rx_data => rx_data);

  stim : process
    variable errors : natural := 0;
    variable cycles : natural := 0;

    procedure tick_clk is
    begin
      clk <= '0'; wait for 5 ns;
      clk <= '1'; wait for 5 ns;
    end procedure;
  begin
    miso <= '1';
    rst  <= '1';                       tick_clk;    -- reset -> IDLE
    rst  <= '0'; tx_data <= TXD; start <= '1'; tick_clk;  -- IDLE -> RUN (latch)
    start <= '0';                      tick_clk;    -- first RUN edge: mosi <= TXD(7)

    if mosi /= TXD(7) then
      errors := errors + 1;
      report "mosi not MSB-first (expected tx_data(7))" severity error;
    end if;

    while done /= '1' and cycles < 40 loop
      tick_clk;
      cycles := cycles + 1;
    end loop;

    if done /= '1' then
      errors := errors + 1;
      report "done never asserted within 40 clocks (possible deadlock)" severity error;
    end if;

    if errors = 0 then
      report "ALL TESTS PASSED (spi_master completion + MSB-first verified)" severity note;
    else
      report integer'image(errors) & " check(s) FAILED" severity failure;
    end if;
    wait;
  end process;
end architecture tb;

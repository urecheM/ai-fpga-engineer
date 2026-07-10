library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity regfile is
  port(clk, we : in std_logic;
       ra1, ra2, wa : in std_logic_vector(4 downto 0);
       wd : in std_logic_vector(31 downto 0);
       rd1, rd2 : out std_logic_vector(31 downto 0));
end entity;
architecture rtl of regfile is
  type rf_t is array(0 to 31) of std_logic_vector(31 downto 0);
  signal rf : rf_t := (others => (others=>'0'));
begin
  process(clk) begin
    if rising_edge(clk) then
      if we='1' and wa /= "00000" then rf(to_integer(unsigned(wa))) <= wd; end if;
    end if;
  end process;
  rd1 <= (others=>'0') when ra1="00000" else rf(to_integer(unsigned(ra1)));
  rd2 <= (others=>'0') when ra2="00000" else rf(to_integer(unsigned(ra2)));
end architecture;

library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity cmp8 is
  port(a, b : in std_logic_vector(7 downto 0);
       gt, eq, lt : out std_logic);
end entity;
architecture rtl of cmp8 is begin
  gt <= '1' when unsigned(a) >  unsigned(b) else '0';
  eq <= '1' when a = b else '0';
  lt <= '1' when unsigned(a) <  unsigned(b) else '0';
end architecture;

library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity adder8 is
  port(a, b : in  std_logic_vector(7 downto 0);
       cin  : in  std_logic;
       sum  : out std_logic_vector(7 downto 0);
       cout : out std_logic);
end entity;
architecture rtl of adder8 is
  signal ext : unsigned(8 downto 0);
begin
  ext  <= ('0' & unsigned(a)) + ('0' & unsigned(b)) + ("00000000" & cin);
  sum  <= std_logic_vector(ext(7 downto 0));
  cout <= ext(8);
end architecture;

library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity adder_w6 is
  port(a, b : in  std_logic_vector(5 downto 0);
       cin  : in  std_logic;
       sum  : out std_logic_vector(5 downto 0);
       cout : out std_logic);
end entity;
architecture rtl of adder_w6 is
  signal ext : unsigned(6 downto 0);
  signal c   : unsigned(6 downto 0);
begin
  c    <= (0 => cin, others => '0');
  ext  <= ('0' & unsigned(a)) + ('0' & unsigned(b)) + c;
  sum  <= std_logic_vector(ext(5 downto 0));
  cout <= ext(6);
end architecture;
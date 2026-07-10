library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity mul8 is
  port(a, b : in std_logic_vector(7 downto 0);
       product : out std_logic_vector(15 downto 0));
end entity;
architecture rtl of mul8 is begin
  product <= std_logic_vector(unsigned(a) * unsigned(b));
end architecture;

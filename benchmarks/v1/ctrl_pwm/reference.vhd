library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity pwm8 is
  port(clk, rst : in std_logic;
       duty : in std_logic_vector(7 downto 0);
       pwm_out : out std_logic);
end entity;
architecture rtl of pwm8 is
  signal cnt : unsigned(7 downto 0) := (others=>'0');
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then cnt <= (others=>'0'); else cnt <= cnt + 1; end if;
    end if;
  end process;
  pwm_out <= '1' when cnt < unsigned(duty) else '0';
end architecture;

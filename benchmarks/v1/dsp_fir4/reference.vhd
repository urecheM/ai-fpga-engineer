library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity fir4 is
  port(clk, rst : in std_logic;
       x : in std_logic_vector(7 downto 0);
       y : out std_logic_vector(11 downto 0));
end entity;
architecture rtl of fir4 is
  type tap_t is array(0 to 3) of signed(7 downto 0);
  signal taps : tap_t := (others => (others=>'0'));
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then taps <= (others => (others=>'0'));
      else taps <= signed(x) & taps(0 to 2); end if;
    end if;
  end process;
  y <= std_logic_vector(resize(taps(0),12) + resize(taps(1)*2,12)
                        + resize(taps(2)*2,12) + resize(taps(3),12));
end architecture;

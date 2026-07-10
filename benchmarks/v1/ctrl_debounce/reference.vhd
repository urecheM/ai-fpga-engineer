library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity debounce is
  port(clk, rst, din : in std_logic; dout : out std_logic);
end entity;
architecture rtl of debounce is
  signal cnt : unsigned(2 downto 0) := (others=>'0');
  signal sync, stable : std_logic := '0';
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then cnt<=(others=>'0'); stable<='0'; sync<=din;
      else
        sync <= din;
        if din /= stable then
          if cnt = 7 then stable <= din; cnt <= (others=>'0');
          else cnt <= cnt + 1; end if;
        else cnt <= (others=>'0'); end if;
      end if;
    end if;
  end process;
  dout <= stable;
end architecture;

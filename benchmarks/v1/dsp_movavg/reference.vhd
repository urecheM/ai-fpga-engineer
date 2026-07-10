library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity movavg4 is
  port(clk, rst : in std_logic;
       x : in std_logic_vector(7 downto 0);
       y : out std_logic_vector(7 downto 0));
end entity;
architecture rtl of movavg4 is
  type w_t is array(0 to 3) of unsigned(7 downto 0);
  signal win : w_t := (others => (others=>'0'));
  signal acc : unsigned(9 downto 0);
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then win <= (others => (others=>'0'));
      else win <= unsigned(x) & win(0 to 2); end if;
    end if;
  end process;
  acc <= resize(win(0),10)+resize(win(1),10)+resize(win(2),10)+resize(win(3),10);
  y <= std_logic_vector(acc(9 downto 2));
end architecture;

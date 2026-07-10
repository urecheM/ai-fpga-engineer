library ieee; use ieee.std_logic_1164.all;
entity traffic_light is
  port(clk, rst, tick : in std_logic;
       lights : out std_logic_vector(2 downto 0));
end entity;
architecture rtl of traffic_light is
  type state_t is (S_RED, S_GREEN, S_YELLOW);
  signal state : state_t;
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst = '1' then state <= S_RED;
      elsif tick = '1' then
        case state is
          when S_RED    => state <= S_GREEN;
          when S_GREEN  => state <= S_YELLOW;
          when S_YELLOW => state <= S_RED;
        end case;
      end if;
    end if;
  end process;
  with state select lights <=
    "100" when S_RED, "010" when S_GREEN, "001" when S_YELLOW;
end architecture;

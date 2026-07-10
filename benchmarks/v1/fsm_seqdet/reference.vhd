library ieee; use ieee.std_logic_1164.all;
entity seq_detect is
  port(clk, rst, din : in std_logic; found : out std_logic);
end entity;
architecture rtl of seq_detect is
  type state_t is (S0, S1, S10, S101);
  signal state : state_t;
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst = '1' then state <= S0;
      else
        case state is
          when S0   => state <= S1   when din='1' else S0;
          when S1   => state <= S1   when din='1' else S10;
          when S10  => state <= S101 when din='1' else S0;
          when S101 => state <= S1   when din='1' else S10;
        end case;
      end if;
    end if;
  end process;
  found <= '1' when (state = S101 and din = '1') else '0';
end architecture;

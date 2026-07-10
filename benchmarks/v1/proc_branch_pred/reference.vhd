library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity branch_pred is
  port(clk, rst, taken : in std_logic; predict : out std_logic);
end entity;
architecture rtl of branch_pred is
  signal ctr : unsigned(1 downto 0) := "01";
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then ctr <= "01";
      elsif taken='1' then if ctr /= "11" then ctr <= ctr + 1; end if;
      else if ctr /= "00" then ctr <= ctr - 1; end if;
      end if;
    end if;
  end process;
  predict <= ctr(1);
end architecture;

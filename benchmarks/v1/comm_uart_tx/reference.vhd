library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity uart_tx is
  port(clk, rst, tick, start : in std_logic;
       data : in std_logic_vector(7 downto 0);
       tx : out std_logic; tx_busy : out std_logic);
end entity;
architecture rtl of uart_tx is
  type st is (IDLE, START_BIT, DATA_BITS, STOP);
  signal state : st := IDLE;
  signal sh : std_logic_vector(7 downto 0);
  signal idx : integer range 0 to 7 := 0;
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then state<=IDLE; tx<='1'; tx_busy<='0'; idx<=0;
      else
        case state is
          when IDLE => tx<='1'; tx_busy<='0';
            if start='1' then sh<=data; tx_busy<='1'; state<=START_BIT; end if;
          when START_BIT => if tick='1' then tx<='0'; idx<=0; state<=DATA_BITS; end if;
          when DATA_BITS => if tick='1' then tx<=sh(idx);
            if idx=7 then state<=STOP; else idx<=idx+1; end if; end if;
          when STOP => if tick='1' then tx<='1'; state<=IDLE; end if;
        end case;
      end if;
    end if;
  end process;
end architecture;

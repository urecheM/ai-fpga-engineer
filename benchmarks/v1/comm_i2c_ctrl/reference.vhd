library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity i2c_byte is
  port(clk, rst, start : in std_logic;
       data : in std_logic_vector(7 downto 0);
       scl, sda, done, ack : out std_logic);
end entity;
architecture rtl of i2c_byte is
  type st is (IDLE, STARTC, SHIFT, ACKB, STOPC);
  signal state : st := IDLE;
  signal sh : std_logic_vector(7 downto 0);
  signal cnt : integer range 0 to 7 := 0;
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then state<=IDLE; done<='0'; scl<='1'; sda<='1'; ack<='0';
      else
        case state is
          when IDLE => done<='0'; scl<='1'; sda<='1';
            if start='1' then sh<=data; cnt<=0; state<=STARTC; end if;
          when STARTC => sda<='0'; state<=SHIFT;
          when SHIFT => scl<='0'; sda<=sh(7); sh<=sh(6 downto 0)&'0';
            if cnt=7 then state<=ACKB; else cnt<=cnt+1; end if;
          when ACKB => ack<='0'; scl<='1'; state<=STOPC;
          when STOPC => sda<='1'; done<='1'; state<=IDLE;
        end case;
      end if;
    end if;
  end process;
end architecture;

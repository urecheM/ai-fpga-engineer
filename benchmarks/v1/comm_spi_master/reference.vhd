library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity spi_master is
  port(clk, rst, start : in std_logic;
       tx_data : in std_logic_vector(7 downto 0);
       miso : in std_logic;
       sclk, mosi, done : out std_logic;
       rx_data : out std_logic_vector(7 downto 0));
end entity;
architecture rtl of spi_master is
  type st is (IDLE, RUN);
  signal state : st := IDLE;
  signal sh_tx, sh_rx : std_logic_vector(7 downto 0);
  signal bit_cnt : integer range 0 to 8 := 0;
  signal clk_ph : std_logic := '0';
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then state<=IDLE; done<='0'; sclk<='0'; bit_cnt<=0;
      else
        case state is
          when IDLE => done<='0'; sclk<='0';
            if start='1' then sh_tx<=tx_data; bit_cnt<=0; clk_ph<='0'; state<=RUN; end if;
          when RUN =>
            clk_ph <= not clk_ph; sclk <= not clk_ph;
            if clk_ph='0' then mosi<=sh_tx(7); sh_tx<=sh_tx(6 downto 0) & '0';
            else sh_rx<=sh_rx(6 downto 0) & miso;
              if bit_cnt=7 then done<='1'; rx_data<=sh_rx(6 downto 0) & miso; state<=IDLE;
              else bit_cnt<=bit_cnt+1; end if;
            end if;
        end case;
      end if;
    end if;
  end process;
end architecture;

library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity fifo16 is
  port(clk, rst, wr_en, rd_en : in std_logic;
       din : in std_logic_vector(7 downto 0);
       dout : out std_logic_vector(7 downto 0);
       full, empty : out std_logic);
end entity;
architecture rtl of fifo16 is
  type mem_t is array(0 to 15) of std_logic_vector(7 downto 0);
  signal mem : mem_t;
  signal wptr, rptr : unsigned(3 downto 0) := (others=>'0');
  signal count : unsigned(4 downto 0) := (others=>'0');
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst='1' then wptr<=(others=>'0'); rptr<=(others=>'0'); count<=(others=>'0');
      else
        if wr_en='1' and count<16 then mem(to_integer(wptr))<=din; wptr<=wptr+1; count<=count+1; end if;
        if rd_en='1' and count>0 then dout<=mem(to_integer(rptr)); rptr<=rptr+1; count<=count-1; end if;
      end if;
    end if;
  end process;
  full  <= '1' when count=16 else '0';
  empty <= '1' when count=0  else '0';
end architecture;

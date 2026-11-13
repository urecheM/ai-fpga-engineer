library ieee; use ieee.std_logic_1164.all;
entity seqdet_p0110 is
  port(clk, rst, din : in std_logic; found : out std_logic);
end entity;
architecture rtl of seqdet_p0110 is
  -- last 3 bits received (oldest in the MSB) and how many are valid
  signal hist  : std_logic_vector(2 downto 0) := (others => '0');
  signal valid : integer range 0 to 3 := 0;
begin
  process(clk) begin
    if rising_edge(clk) then
      if rst = '1' then
        hist <= (others => '0'); valid <= 0;
      else
        hist <= hist(1 downto 0) & din;
        if valid < 3 then valid <= valid + 1; end if;
      end if;
    end if;
  end process;
  found <= '1' when valid = 3 and (hist & din) = "0110" else '0';
end architecture;
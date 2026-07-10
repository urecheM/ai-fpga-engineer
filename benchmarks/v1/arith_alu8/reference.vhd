library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity alu8 is
  port(a, b   : in  std_logic_vector(7 downto 0);
       opcode : in  std_logic_vector(2 downto 0);
       result : out std_logic_vector(7 downto 0);
       zero   : out std_logic);
end entity;
architecture rtl of alu8 is
  signal r : std_logic_vector(7 downto 0);
begin
  process(a, b, opcode) begin
    case opcode is
      when "000" => r <= std_logic_vector(unsigned(a) + unsigned(b));
      when "001" => r <= std_logic_vector(unsigned(a) - unsigned(b));
      when "010" => r <= a and b;
      when "011" => r <= a or b;
      when "100" => r <= a xor b;
      when others => r <= (others => '0');
    end case;
  end process;
  result <= r;
  zero   <= '1' when r = "00000000" else '0';
end architecture;

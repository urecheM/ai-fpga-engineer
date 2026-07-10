library ieee; use ieee.std_logic_1164.all;
entity alu_control is
  port(alu_op : in std_logic_vector(1 downto 0);
       funct  : in std_logic_vector(3 downto 0);
       alu_ctl : out std_logic_vector(3 downto 0));
end entity;
architecture rtl of alu_control is begin
  process(alu_op, funct) begin
    case alu_op is
      when "00" => alu_ctl <= "0010";              -- add (lw/sw)
      when "01" => alu_ctl <= "0110";              -- sub (beq)
      when others =>
        case funct is
          when "0000" => alu_ctl <= "0010";
          when "0010" => alu_ctl <= "0110";
          when "0100" => alu_ctl <= "0000";
          when "0101" => alu_ctl <= "0001";
          when "1010" => alu_ctl <= "0111";
          when others => alu_ctl <= "1111";
        end case;
    end case;
  end process;
end architecture;

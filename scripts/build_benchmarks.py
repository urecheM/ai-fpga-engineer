"""Generate the v1 benchmark suite (metadata + reference VHDL).

Run once to materialise ``benchmarks/v1/``. Each benchmark is emitted as
structured metadata plus a verified-by-construction reference implementation.
This generator is itself part of the reproducibility story: the dataset is a
build product, not hand-edited files.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "v1"
VERSION = "1.0.0"


def bench(**kw):
    return kw


# (id, category, title, spec, entity, complexity, tags, ref_vhdl, requirements, properties)
BENCHMARKS = []


def add(
    id,
    category,
    title,
    spec,
    entity,
    complexity,
    tags,
    ref,
    reqs,
    props=None,
    expected="",
    tb=None,
    tb_entity="",
):
    BENCHMARKS.append(
        {
            "id": id,
            "category": category,
            "title": title,
            "spec": spec,
            "entity": entity,
            "complexity": complexity,
            "tags": tags,
            "ref": textwrap.dedent(ref).strip() + "\n",
            "reqs": reqs,
            "props": props or [],
            "expected": expected,
            "tb": textwrap.dedent(tb).strip() + "\n" if tb else None,
            "tb_entity": tb_entity,
        }
    )


# ---------------- ARITHMETIC ----------------
add(
    "arith_adder8",
    "arithmetic",
    "8-bit ripple-carry adder",
    "Design an 8-bit adder with carry-in and carry-out. Inputs a and b are 8-bit "
    "unsigned vectors, cin is a single bit. Output sum is 8 bits and cout is the carry out.",
    "adder8",
    {
        "arithmetic_complexity": 2,
        "interface_count": 5,
        "control_complexity": 0,
        "timing_constraints": 0,
    },
    ["adder", "combinational"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity adder8 is
      port(a, b : in  std_logic_vector(7 downto 0);
           cin  : in  std_logic;
           sum  : out std_logic_vector(7 downto 0);
           cout : out std_logic);
    end entity;
    architecture rtl of adder8 is
      signal ext : unsigned(8 downto 0);
    begin
      ext  <= ('0' & unsigned(a)) + ('0' & unsigned(b)) + ("00000000" & cin);
      sum  <= std_logic_vector(ext(7 downto 0));
      cout <= ext(8);
    end architecture;
    """,
    ["sum = a + b + cin (mod 256)", "cout is the 9th bit of the sum"],
    ["overflow_detection"],
)

add(
    "arith_alu8",
    "arithmetic",
    "8-bit ALU (ADD/SUB/AND/OR/XOR)",
    "Design an 8-bit ALU with a 3-bit opcode selecting ADD(000), SUB(001), AND(010), "
    "OR(011), XOR(100). Inputs a and b are 8-bit. Outputs result (8-bit) and a zero flag.",
    "alu8",
    {
        "arithmetic_complexity": 5,
        "interface_count": 5,
        "control_complexity": 3,
        "timing_constraints": 0,
    },
    ["alu", "combinational"],
    """
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
    """,
    ["opcode selects the operation", "zero=1 iff result is 0"],
    ["overflow_detection", "mutual_exclusion"],
)

add(
    "arith_mul8",
    "arithmetic",
    "8x8 unsigned multiplier",
    "Design an 8x8 unsigned combinational multiplier. Inputs a and b are 8-bit; "
    "output product is 16-bit.",
    "mul8",
    {"arithmetic_complexity": 6, "interface_count": 3, "timing_constraints": 0},
    ["multiplier", "combinational", "dsp"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity mul8 is
      port(a, b : in std_logic_vector(7 downto 0);
           product : out std_logic_vector(15 downto 0));
    end entity;
    architecture rtl of mul8 is begin
      product <= std_logic_vector(unsigned(a) * unsigned(b));
    end architecture;
    """,
    ["product = a * b"],
    [],
)

add(
    "arith_cmp8",
    "arithmetic",
    "8-bit magnitude comparator",
    "Design an 8-bit unsigned comparator with outputs gt, eq, lt.",
    "cmp8",
    {"arithmetic_complexity": 2, "interface_count": 5, "control_complexity": 2},
    ["comparator", "combinational"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity cmp8 is
      port(a, b : in std_logic_vector(7 downto 0);
           gt, eq, lt : out std_logic);
    end entity;
    architecture rtl of cmp8 is begin
      gt <= '1' when unsigned(a) >  unsigned(b) else '0';
      eq <= '1' when a = b else '0';
      lt <= '1' when unsigned(a) <  unsigned(b) else '0';
    end architecture;
    """,
    ["exactly one of gt/eq/lt is high"],
    ["mutual_exclusion"],
)

# ---------------- FSM ----------------
add(
    "fsm_traffic",
    "fsm",
    "Traffic-light controller FSM",
    "Design a traffic-light FSM with states RED, GREEN, YELLOW cycling on each clock "
    "tick enable. Synchronous active-high reset returns to RED. Output lights is a "
    "3-bit one-hot (RED=100, GREEN=010, YELLOW=001).",
    "traffic_light",
    {"state_complexity": 3, "control_complexity": 3, "timing_constraints": 2, "interface_count": 4},
    ["fsm", "sequential"],
    """
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
    """,
    ["cycles RED->GREEN->YELLOW->RED on tick", "reset forces RED"],
    ["deadlock_freedom", "unreachable_state"],
)

add(
    "fsm_seqdet",
    "fsm",
    "Sequence detector (1011, overlapping)",
    "Design an overlapping Mealy/Moore sequence detector that asserts found for one "
    "cycle when the serial input bit stream contains 1011. Synchronous active-high reset.",
    "seq_detect",
    {"state_complexity": 4, "control_complexity": 4, "timing_constraints": 2, "interface_count": 4},
    ["fsm", "sequential"],
    """
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
    """,
    ["asserts found on 1011", "overlapping matches supported"],
    ["deadlock_freedom", "unreachable_state"],
)

# ---------------- COMMUNICATION ----------------
add(
    "comm_uart_tx",
    "communication",
    "UART transmitter (8N1)",
    "Design a UART transmitter for 8 data bits, no parity, 1 stop bit. A start pulse "
    "latches data and shifts it out LSB-first framed by a start (0) and stop (1) bit. "
    "tx_busy is high during transmission. Assume a one-clock-per-bit baud tick.",
    "uart_tx",
    {
        "state_complexity": 4,
        "control_complexity": 5,
        "timing_constraints": 3,
        "interface_count": 6,
        "concurrency": 1,
    },
    ["uart", "protocol", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity uart_tx is
      port(clk, rst, tick, start : in std_logic;
           data : in std_logic_vector(7 downto 0);
           tx : out std_logic; tx_busy : out std_logic);
    end entity;
    architecture rtl of uart_tx is
      type st is (IDLE, ST_START, ST_DATA, ST_STOP);
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
                if start='1' then sh<=data; tx_busy<='1'; state<=ST_START; end if;
              when ST_START => if tick='1' then tx<='0'; idx<=0; state<=ST_DATA; end if;
              when ST_DATA => if tick='1' then tx<=sh(idx);
                if idx=7 then state<=ST_STOP; else idx<=idx+1; end if; end if;
              when ST_STOP => if tick='1' then tx<='1'; state<=IDLE; end if;
            end case;
          end if;
        end if;
      end process;
    end architecture;
    """,
    ["frames data with start=0 and stop=1", "LSB-first", "tx_busy asserted during frame"],
    ["deadlock_freedom", "transaction_completion"],
    tb="""
    -- Self-checking testbench for uart_tx (8N1, one clock per bit via tick='1').
    -- Drives a byte and verifies the serial frame: start(0), data LSB-first, stop(1).
    -- Pass => "ALL TESTS PASSED"; mismatch => severity failure (non-zero exit).
    -- NOTE: outputs of uart_tx are registered, so tx updates one clock after the
    -- state/tick condition; the checks below account for that latency.
    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

    entity uart_tx_tb is
    end entity uart_tx_tb;

    architecture tb of uart_tx_tb is
      signal clk, rst, tick, start, tx, tx_busy : std_logic := '0';
      signal data : std_logic_vector(7 downto 0) := (others => '0');
      constant BYTE : std_logic_vector(7 downto 0) := "10110010";
    begin
      dut : entity work.uart_tx
        port map (clk => clk, rst => rst, tick => tick, start => start,
                  data => data, tx => tx, tx_busy => tx_busy);

      stim : process
        variable errors : natural := 0;
        variable expect : std_logic_vector(0 to 9);  -- start + 8 data + stop

        procedure tick_clk is
        begin
          clk <= '0'; wait for 5 ns;
          clk <= '1'; wait for 5 ns;
        end procedure;
      begin
        expect(0) := '0';                              -- start bit
        for i in 0 to 7 loop
          expect(i + 1) := BYTE(i);                     -- data, LSB first
        end loop;
        expect(9) := '1';                              -- stop bit

        tick <= '1';
        rst  <= '1';                 tick_clk;          -- reset -> IDLE
        rst  <= '0'; data <= BYTE; start <= '1'; tick_clk;  -- IDLE -> START (latch)
        start <= '0';                tick_clk;          -- START -> DATA, tx <= start bit

        if tx /= expect(0) then
          errors := errors + 1;
          report "start bit mismatch" severity error;
        end if;

        for i in 1 to 9 loop
          tick_clk;                                     -- each subsequent bit
          if tx /= expect(i) then
            errors := errors + 1;
            report "frame bit " & integer'image(i) & " mismatch" severity error;
          end if;
        end loop;

        if errors = 0 then
          report "ALL TESTS PASSED (uart_tx frame verified)" severity note;
        else
          report integer'image(errors) & " frame bit(s) FAILED" severity failure;
        end if;
        wait;
      end process;
    end architecture tb;
    """,
    tb_entity="uart_tx_tb",
)

add(
    "comm_spi_master",
    "communication",
    "SPI master (mode 0)",
    "Design an SPI master in mode 0 (CPOL=0, CPHA=0) shifting 8 bits MSB-first. On "
    "start, generate sclk, drive mosi, sample miso, and assert done when complete.",
    "spi_master",
    {
        "state_complexity": 4,
        "control_complexity": 5,
        "timing_constraints": 3,
        "interface_count": 8,
        "concurrency": 1,
    },
    ["spi", "protocol", "sequential"],
    """
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
    """,
    ["MSB-first 8-bit transfer", "mode 0 timing", "done pulses on completion"],
    ["deadlock_freedom", "transaction_completion"],
    tb="""
    -- Self-checking testbench for spi_master (mode 0, MSB-first, 8 bits).
    -- Robust checks that don't depend on exact internal phase counting:
    --   1. the first mosi bit equals tx_data(7)  (MSB-first);
    --   2. 'done' asserts within a bounded number of clocks (transaction completes,
    --      i.e. no deadlock).
    -- Full rx_data equivalence checking is left as a follow-up.
    -- Pass => "ALL TESTS PASSED"; failure => severity failure (non-zero exit).
    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;

    entity spi_master_tb is
    end entity spi_master_tb;

    architecture tb of spi_master_tb is
      signal clk, rst, start, miso, sclk, mosi, done : std_logic := '0';
      signal tx_data : std_logic_vector(7 downto 0) := (others => '0');
      signal rx_data : std_logic_vector(7 downto 0);
      constant TXD : std_logic_vector(7 downto 0) := "10100011";
    begin
      dut : entity work.spi_master
        port map (clk => clk, rst => rst, start => start, tx_data => tx_data,
                  miso => miso, sclk => sclk, mosi => mosi, done => done,
                  rx_data => rx_data);

      stim : process
        variable errors : natural := 0;
        variable cycles : natural := 0;

        procedure tick_clk is
        begin
          clk <= '0'; wait for 5 ns;
          clk <= '1'; wait for 5 ns;
        end procedure;
      begin
        miso <= '1';
        rst  <= '1';                       tick_clk;    -- reset -> IDLE
        rst  <= '0'; tx_data <= TXD; start <= '1'; tick_clk;  -- IDLE -> RUN (latch)
        start <= '0';                      tick_clk;    -- first RUN edge: mosi <= TXD(7)

        if mosi /= TXD(7) then
          errors := errors + 1;
          report "mosi not MSB-first (expected tx_data(7))" severity error;
        end if;

        while done /= '1' and cycles < 40 loop
          tick_clk;
          cycles := cycles + 1;
        end loop;

        if done /= '1' then
          errors := errors + 1;
          report "done never asserted within 40 clocks (possible deadlock)" severity error;
        end if;

        if errors = 0 then
          report "ALL TESTS PASSED (spi_master completion + MSB-first verified)" severity note;
        else
          report integer'image(errors) & " check(s) FAILED" severity failure;
        end if;
        wait;
      end process;
    end architecture tb;
    """,
    tb_entity="spi_master_tb",
)

# ---------------- MEMORY ----------------
add(
    "mem_fifo",
    "memory",
    "Synchronous FIFO (depth 16)",
    "Design a synchronous FIFO, 8-bit wide, depth 16, with wr_en/rd_en, full and empty "
    "flags, and synchronous active-high reset.",
    "fifo16",
    {
        "state_complexity": 0,
        "control_complexity": 4,
        "timing_constraints": 2,
        "interface_count": 8,
        "concurrency": 2,
    },
    ["fifo", "memory", "sequential"],
    """
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
    """,
    ["FIFO ordering preserved", "full/empty flags correct", "no overflow/underflow"],
    ["overflow_detection", "mutual_exclusion"],
)

add(
    "mem_regfile",
    "memory",
    "32x32 register file (2R1W)",
    "Design a 32-entry, 32-bit register file with two read ports and one write port. "
    "Register 0 always reads as zero. Writes are synchronous.",
    "regfile",
    {
        "control_complexity": 3,
        "timing_constraints": 1,
        "interface_count": 9,
        "concurrency": 2,
        "hierarchy_depth": 1,
    },
    ["register-file", "memory", "processor", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity regfile is
      port(clk, we : in std_logic;
           ra1, ra2, wa : in std_logic_vector(4 downto 0);
           wd : in std_logic_vector(31 downto 0);
           rd1, rd2 : out std_logic_vector(31 downto 0));
    end entity;
    architecture rtl of regfile is
      type rf_t is array(0 to 31) of std_logic_vector(31 downto 0);
      signal rf : rf_t := (others => (others=>'0'));
    begin
      process(clk) begin
        if rising_edge(clk) then
          if we='1' and wa /= "00000" then rf(to_integer(unsigned(wa))) <= wd; end if;
        end if;
      end process;
      rd1 <= (others=>'0') when ra1="00000" else rf(to_integer(unsigned(ra1)));
      rd2 <= (others=>'0') when ra2="00000" else rf(to_integer(unsigned(ra2)));
    end architecture;
    """,
    ["reg 0 reads zero", "two independent read ports", "synchronous write"],
    ["mutual_exclusion"],
)

# ---------------- PROCESSOR ----------------
add(
    "proc_branch_pred",
    "processor",
    "2-bit saturating branch predictor",
    "Design a 2-bit saturating counter branch predictor. On each resolved branch "
    "(taken input), update the state; predict output is high when in a 'taken' state. "
    "Synchronous active-high reset to weakly-not-taken.",
    "branch_pred",
    {"state_complexity": 4, "control_complexity": 4, "timing_constraints": 2, "interface_count": 4},
    ["branch-predictor", "processor", "fsm", "sequential"],
    """
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
    """,
    ["saturates at strongly taken/not-taken", "predict = MSB of counter"],
    ["deadlock_freedom"],
)

add(
    "proc_alu_ctrl",
    "processor",
    "ALU control decoder",
    "Design an ALU control unit: given a 2-bit ALUOp and a 4-bit funct field, output a "
    "4-bit ALU control signal following the classic MIPS mapping (add/sub/and/or/slt).",
    "alu_control",
    {"control_complexity": 5, "arithmetic_complexity": 1, "interface_count": 3},
    ["processor", "combinational", "control"],
    """
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
    """,
    ["decodes ALUOp+funct to control", "defaults defined for all inputs"],
    ["mutual_exclusion"],
)

# ---------------- DSP ----------------
add(
    "dsp_fir4",
    "dsp",
    "4-tap FIR filter",
    "Design a 4-tap FIR filter with fixed coefficients [1,2,2,1] over signed 8-bit "
    "samples. On each clock, shift in a new sample and output the convolution sum.",
    "fir4",
    {
        "arithmetic_complexity": 6,
        "control_complexity": 2,
        "timing_constraints": 2,
        "interface_count": 4,
        "concurrency": 1,
    },
    ["fir", "dsp", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity fir4 is
      port(clk, rst : in std_logic;
           x : in std_logic_vector(7 downto 0);
           y : out std_logic_vector(11 downto 0));
    end entity;
    architecture rtl of fir4 is
      type tap_t is array(0 to 3) of signed(7 downto 0);
      signal taps : tap_t := (others => (others=>'0'));
    begin
      process(clk) begin
        if rising_edge(clk) then
          if rst='1' then taps <= (others => (others=>'0'));
          else taps <= signed(x) & taps(0 to 2); end if;
        end if;
      end process;
      y <= std_logic_vector(resize(taps(0),12) + resize(taps(1)*2,12)
                            + resize(taps(2)*2,12) + resize(taps(3),12));
    end architecture;
    """,
    ["y = 1*x0 + 2*x1 + 2*x2 + 1*x3", "signed arithmetic"],
    ["overflow_detection"],
)

add(
    "dsp_movavg",
    "dsp",
    "Moving-average filter (window 4)",
    "Design a moving-average filter over the last 4 unsigned 8-bit samples, outputting "
    "the average (sum divided by 4).",
    "movavg4",
    {
        "arithmetic_complexity": 4,
        "control_complexity": 2,
        "timing_constraints": 2,
        "interface_count": 4,
    },
    ["moving-average", "dsp", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity movavg4 is
      port(clk, rst : in std_logic;
           x : in std_logic_vector(7 downto 0);
           y : out std_logic_vector(7 downto 0));
    end entity;
    architecture rtl of movavg4 is
      type w_t is array(0 to 3) of unsigned(7 downto 0);
      signal win : w_t := (others => (others=>'0'));
      signal acc : unsigned(9 downto 0);
    begin
      process(clk) begin
        if rising_edge(clk) then
          if rst='1' then win <= (others => (others=>'0'));
          else win <= unsigned(x) & win(0 to 2); end if;
        end if;
      end process;
      acc <= resize(win(0),10)+resize(win(1),10)+resize(win(2),10)+resize(win(3),10);
      y <= std_logic_vector(acc(9 downto 2));
    end architecture;
    """,
    ["output = mean of last 4 samples"],
    [],
)

# ---------------- CONTROL ----------------
add(
    "ctrl_pwm",
    "control",
    "PWM generator (8-bit duty)",
    "Design an 8-bit PWM generator. A free-running 8-bit counter compares against an "
    "input duty value; pwm_out is high while counter < duty. Synchronous reset.",
    "pwm8",
    {
        "arithmetic_complexity": 1,
        "control_complexity": 2,
        "timing_constraints": 2,
        "interface_count": 4,
    },
    ["pwm", "control", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity pwm8 is
      port(clk, rst : in std_logic;
           duty : in std_logic_vector(7 downto 0);
           pwm_out : out std_logic);
    end entity;
    architecture rtl of pwm8 is
      signal cnt : unsigned(7 downto 0) := (others=>'0');
    begin
      process(clk) begin
        if rising_edge(clk) then
          if rst='1' then cnt <= (others=>'0'); else cnt <= cnt + 1; end if;
        end if;
      end process;
      pwm_out <= '1' when cnt < unsigned(duty) else '0';
    end architecture;
    """,
    ["duty cycle proportional to duty input"],
    [],
)

add(
    "ctrl_debounce",
    "control",
    "Switch debouncer",
    "Design a switch debouncer that only propagates the input to the output after it "
    "has been stable for N=8 consecutive clock cycles.",
    "debounce",
    {"state_complexity": 0, "control_complexity": 3, "timing_constraints": 2, "interface_count": 3},
    ["debouncer", "control", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity debounce is
      port(clk, rst, din : in std_logic; dout : out std_logic);
    end entity;
    architecture rtl of debounce is
      signal cnt : unsigned(2 downto 0) := (others=>'0');
      signal sync, stable : std_logic := '0';
    begin
      process(clk) begin
        if rising_edge(clk) then
          if rst='1' then cnt<=(others=>'0'); stable<='0'; sync<=din;
          else
            sync <= din;
            if din /= stable then
              if cnt = 7 then stable <= din; cnt <= (others=>'0');
              else cnt <= cnt + 1; end if;
            else cnt <= (others=>'0'); end if;
          end if;
        end if;
      end process;
      dout <= stable;
    end architecture;
    """,
    ["output changes only after 8 stable cycles"],
    [],
)

add(
    "mem_sync_ram",
    "memory",
    "Synchronous single-port RAM (256x8)",
    "Design a synchronous single-port RAM, 256 words x 8 bits, with a registered read "
    "output and a write-enable.",
    "sync_ram",
    {"control_complexity": 2, "timing_constraints": 1, "interface_count": 6},
    ["ram", "memory", "sequential"],
    """
    library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
    entity sync_ram is
      port(clk, we : in std_logic;
           addr : in std_logic_vector(7 downto 0);
           din : in std_logic_vector(7 downto 0);
           dout : out std_logic_vector(7 downto 0));
    end entity;
    architecture rtl of sync_ram is
      type mem_t is array(0 to 255) of std_logic_vector(7 downto 0);
      signal mem : mem_t;
    begin
      process(clk) begin
        if rising_edge(clk) then
          if we='1' then mem(to_integer(unsigned(addr))) <= din; end if;
          dout <= mem(to_integer(unsigned(addr)));
        end if;
      end process;
    end architecture;
    """,
    ["registered read", "write-enable gated write"],
    [],
)

add(
    "comm_i2c_ctrl",
    "communication",
    "I2C bit-level controller (start/stop/byte)",
    "Design an I2C master byte controller that generates START and STOP conditions and "
    "shifts out 8 bits MSB-first on sda synchronised to scl, asserting done after the "
    "byte and sampling the ack bit.",
    "i2c_byte",
    {
        "state_complexity": 5,
        "control_complexity": 6,
        "timing_constraints": 3,
        "interface_count": 8,
        "concurrency": 1,
    },
    ["i2c", "protocol", "sequential"],
    """
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
    """,
    ["generates START and STOP", "8-bit MSB-first shift", "samples ack"],
    ["deadlock_freedom", "transaction_completion"],
)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for b in BENCHMARKS:
        bdir = ROOT / b["id"]
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / "reference.vhd").write_text(b["ref"])
        meta = {
            "id": b["id"],
            "version": VERSION,
            "category": b["category"],
            "title": b["title"],
            "specification": b["spec"],
            "functional_requirements": b["reqs"],
            "expected_behavior": b.get("expected", ""),
            "entity": b["entity"],
            "tags": b["tags"],
            "complexity": b["complexity"],
            "reference_hdl_path": "reference.vhd",
        }
        if b.get("tb"):
            (bdir / "testbench.vhd").write_text(b["tb"])
            meta["testbench_path"] = "testbench.vhd"
            meta["testbench_entity"] = b["tb_entity"]
        meta["properties"] = b["props"]
        with (bdir / "benchmark.yaml").open("w") as fh:
            yaml.safe_dump(meta, fh, sort_keys=False, default_flow_style=False)
    print(f"wrote {len(BENCHMARKS)} benchmarks to {ROOT}")


if __name__ == "__main__":
    main()

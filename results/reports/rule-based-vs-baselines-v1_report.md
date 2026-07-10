# Results: rule-based-vs-baselines-v1
_This report is generated automatically from the experiment registry._

## Overall leaderboard

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| synthetic-high | direct | 18 | 1.0 | [0.8241, 1.0] | 1.0 | 0.0 | 1.7361 | 298.2 | 0.0 |
| reference-golden | direct | 18 | 1.0 | [0.8241, 1.0] | 1.0 | 0.0 | 0.0998 | 320.3 | 0.0 |
| rule-based | direct | 18 | 0.3889 | [0.203, 0.6138] | 0.3889 | 0.0 | 0.0007 | 266.9 | 0.0 |

## Category: arithmetic

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 4 | 0.5 | [0.15, 0.85] | 0.5 | 0.0 | 0.0021 | 292.0 | 0.0 |
| synthetic-high | direct | 4 | 1.0 | [0.5101, 1.0] | 1.0 | 0.0 | 1.3793 | 236.0 | 0.0 |
| reference-golden | direct | 4 | 1.0 | [0.5101, 1.0] | 1.0 | 0.0 | 0.1028 | 250.5 | 0.0 |

## Category: communication

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 3 | 0.0 | [0.0, 0.5615] | 0.0 | 0.0 | 0.0002 | 166.0 | 0.0 |
| synthetic-high | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 2.2107 | 417.3 | 0.0 |
| reference-golden | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 0.102 | 433.0 | 0.0 |

## Category: control

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 2 | 0.5 | [0.0945, 0.9055] | 0.5 | 0.0 | 0.0003 | 369.5 | 0.0 |
| synthetic-high | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 1.514 | 271.0 | 0.0 |
| reference-golden | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 0.088 | 285.5 | 0.0 |

## Category: dsp

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 2 | 0.0 | [0.0, 0.6576] | 0.0 | 0.0 | 0.0002 | 151.0 | 0.0 |
| synthetic-high | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 1.8735 | 296.0 | 0.0 |
| reference-golden | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 0.104 | 310.0 | 0.0 |

## Category: fsm

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 2 | 0.0 | [0.0, 0.6576] | 0.0 | 0.0 | 0.0002 | 163.5 | 0.0 |
| synthetic-high | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 2.1005 | 312.5 | 0.0 |
| reference-golden | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 0.082 | 329.0 | 0.0 |

## Category: memory

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 3 | 0.6667 | [0.2077, 0.9385] | 0.6667 | 0.0 | 0.0003 | 270.3 | 0.0 |
| synthetic-high | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 1.663 | 293.0 | 0.0 |
| reference-golden | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 0.1047 | 327.7 | 0.0 |

## Category: processor

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 0.0005 | 479.5 | 0.0 |
| synthetic-high | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 1.568 | 266.5 | 0.0 |
| reference-golden | direct | 2 | 1.0 | [0.3424, 1.0] | 1.0 | 0.0 | 0.1085 | 316.5 | 0.0 |

## Difficulty tier: trivial

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 1 | 0.0 | [0.0, 0.7935] | 0.0 | 0.0 | 0.0074 | 158.0 | 0.0 |
| synthetic-high | direct | 1 | 1.0 | [0.2065, 1.0] | 1.0 | 0.0 | 0.839 | 245.0 | 0.0 |
| reference-golden | direct | 1 | 1.0 | [0.2065, 1.0] | 1.0 | 0.0 | 0.116 | 259.0 | 0.0 |

## Difficulty tier: easy

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 8 | 0.5 | [0.2152, 0.7848] | 0.5 | 0.0 | 0.0004 | 298.9 | 0.0 |
| synthetic-high | direct | 8 | 1.0 | [0.6756, 1.0] | 1.0 | 0.0 | 1.5253 | 257.6 | 0.0 |
| reference-golden | direct | 8 | 1.0 | [0.6756, 1.0] | 1.0 | 0.0 | 0.1026 | 280.2 | 0.0 |

## Difficulty tier: moderate

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 6 | 0.5 | [0.1876, 0.8124] | 0.5 | 0.0 | 0.0003 | 292.8 | 0.0 |
| synthetic-high | direct | 6 | 1.0 | [0.6097, 1.0] | 1.0 | 0.0 | 1.9295 | 301.5 | 0.0 |
| reference-golden | direct | 6 | 1.0 | [0.6097, 1.0] | 1.0 | 0.0 | 0.0922 | 327.7 | 0.0 |

## Difficulty tier: hard

| model | prompt | n | pass_rate | pass_ci95 | compile_rate | synth_rate | avg_latency_s | avg_tokens | avg_retries |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule-based | direct | 3 | 0.0 | [0.0, 0.5615] | 0.0 | 0.0 | 0.0002 | 166.0 | 0.0 |
| synthetic-high | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 2.2107 | 417.3 | 0.0 |
| reference-golden | direct | 3 | 1.0 | [0.4385, 1.0] | 1.0 | 0.0 | 0.102 | 433.0 | 0.0 |

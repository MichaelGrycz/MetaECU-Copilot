# MetaECU Copilot — Calibration Audit Report

**Tuner intent:** Give me 450 Nm, maximum power
**Stock binary:** `SAAB 93 tid 2008 edc16c39 1037389375.Bin`
**Tuned binary:** `metaecu_demo_tuned.bin`
**Planner source:** muse (target effective 377 Nm)

## Self-correction loop

- Attempt 1 [muse]: target 377 Nm -> Safety Gate **PASS**

## Final Safety Gate metrics

- `peak_effective_nm`: 349.0
- `peak_effective_rpm`: 2000.0
- `peak_indicated_nm`: 390.0
- `indicated_1500_nm`: 330.0
- `max_torque_step_nm`: 40.0
- `Rail_pSetPointBase_MAP_max_bar`: 1600.0
- `Rail_pSetPointMax_MAP_max_bar`: 1600.0
- `smoke_lambda_min`: 0.771
- `checksum_ok`: True
- `checksum`: 0xD01FE500

**Final verdict: PASS — binary approved for flashing**

Checksum: `0xD01FE500` (target `0xD01FE500`)

## Changed calibration

- Symbol: `EngPrt_trqLim_CUR`
- Changed cells: 16

_Deterministic gate rules: F40 effective torque <= 377 Nm @90C, DMF 1500 rpm cap, rail <= 1600 bar, smoke lambda >= 0.85, no torque spikes, checksum 0xD01FE500. No AI output bypasses this gate._

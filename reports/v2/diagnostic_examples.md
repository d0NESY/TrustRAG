# V2 逐题诊断示例

全部失败与成功保存在原始 predictions/CSV。以下按固定排序取每种条件最前面的最多三例，仅用于阅读，不改变指标或 gold。

## dense → dense_reranker：improved

| id | category | question | before | after |
| --- | --- | --- | --- | --- |
| v2_access_keys_exact_term | exact_term | What state does IAM-552 identify in the key-management console? | 3 | 1 |
| v2_access_keys_version_conflict | version_conflict | What rotation interval is mandated by the active API credential standard? | 3 | 1 |
| v2_backup_restore_version_conflict | version_conflict | What retention applies to tenant snapshots under today's recovery schedule? | 3 | 1 |

## dense → dense_reranker：degraded

没有符合条件的 test case。

## hybrid → hybrid_reranker：improved

| id | category | question | before | after |
| --- | --- | --- | --- | --- |
| v2_access_keys_version_conflict | version_conflict | What rotation interval is mandated by the active API credential standard? | 2 | 1 |
| v2_backup_restore_version_conflict | version_conflict | What retention applies to tenant snapshots under today's recovery schedule? | 2 | 1 |
| v2_customs_returns_version_conflict | version_conflict | What broker lead time is required by the current return shipping instruction? | 2 | 1 |

## hybrid → hybrid_reranker：degraded

| id | category | question | before | after |
| --- | --- | --- | --- | --- |
| v2_warehouse_spills_cross_document | cross_document | Where should an operator find the disposal container code after the lane is made safe? | 1 | 2 |

## G1 新增误拒答

- `v2_device_exit_exact_term`，top1=0.016206。Question: Which asset problem should be filed on OFF-217 rather than a payroll ticket?

  Gold: missing accessories at device return

  G0: A departing employee must hand company hardware to the endpoint custodian within five business days after termination and Form OFF-217 records missing accessories at device return; it does not authorize a salary deduction. [S1]

  G1: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.

- `v2_hotel_travel_semantic`，top1=0.022978。Question: If work keeps me away overnight, which proof shows that the room bill was actually settled?

  Gold: a paid hotel folio

  G0: An overnight business traveler must attach a paid hotel folio showing settlement; a reservation email alone is insufficient. [S1]

  G1: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.

- `v2_warehouse_spills_cross_document`，top1=0.021136。Question: Where should an operator find the disposal container code after the lane is made safe?

  Gold: the waste classification annex; WST-44

  G0: The waste classification annex assigns container WST-44 to used solvent absorbent. [S2]

  G1: I couldn't find sufficient evidence in the current knowledge base to answer this question reliably.

## G0 near-miss false answer

- `v2_rail_booking_near_miss_2`，top1=0.977644。Question: Which client allows employees to claim first-class rail travel?

  Gold: None

  G0: Executives travelling on client business may book first class. [S1]

  G1: Executives travelling on client business may book first class. [S1]

## G1 near-miss false answer

- `v2_rail_booking_near_miss_2`，top1=0.977644。Question: Which client allows employees to claim first-class rail travel?

  Gold: None

  G0: Executives travelling on client business may book first class. [S1]

  G1: Executives travelling on client business may book first class. [S1]

## Score 尾部反例

- `v2_rail_booking_near_miss_2`，answerable=False，top1=0.977644。Question: Which client allows employees to claim first-class rail travel?

  Gold: None

  G0: Executives travelling on client business may book first class. [S1]

- `v2_device_exit_exact_term`，answerable=True，top1=0.016206。Question: Which asset problem should be filed on OFF-217 rather than a payroll ticket?

  Gold: missing accessories at device return

  G0: A departing employee must hand company hardware to the endpoint custodian within five business days after termination and Form OFF-217 records missing accessories at device return; it does not authorize a salary deduction. [S1]


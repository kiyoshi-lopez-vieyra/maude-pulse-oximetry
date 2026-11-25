# Post-market risk review for pulse oximeters (inspired by ISO 14971:2019, clause 10)

> Learning exercise based only on public MAUDE data. It is **inspired by** ISO 14971 and does not claim compliance. Severity ratings are the author's engineering judgment (approved 2026-11-24). Probability is **not** estimated, because MAUDE has no data on how many devices are in use.

## Severity scale used
| Level | Definition |
|---|---|
| High | The failure can contribute to death or permanent harm, typically because a dangerous patient condition goes undetected. |
| Medium | Temporary or reversible harm, or a hazardous situation that staff normally notice in time. |
| Low–Medium | Inconvenience or an unusable device, with harm unlikely. |

## Evidence used
- **Failure category per report:** predicted by the keyword model (`src/predict_all.py`) for the 13,937 DQA reports with an event description. Model quality: macro-F1 0.60 on the labeled test set (`docs/model_card.md`).
- **Calibration caveat:** the model under-predicts `accuracy`, `signal_acquisition` and `software_behavior`, and 22.6% of reports match no keyword. Counts below are therefore **lower bounds** for those categories (`docs/trends.md`, section 2).
- **"Death" / "Injury"** is the event type chosen by the reporter: it means a death or injury was mentioned, **not** that the device caused it.

## Hazard table
| Failure category | Hazardous situation (example) | Possible harm | Severity (approved) | Reports | Death / Injury reports | Signals 2023–2026 (`docs/trends.md`) |
|---|---|---|---|---|---|---|
| `alarm` | Desaturation or bradycardia occurs and no alarm is heard or seen. | Delayed treatment of hypoxemia; possible death. | **High** | 2,889 | 187 / 77 | Jul–Dec 2025, mostly one manufacturer group; confirmed by FDA terms. |
| `accuracy` (falsely high) | Monitor shows normal SpO2 while the real value is low. | Hidden hypoxemia; possible death. | **High** | 1,816 (both directions) | 33 / 64 | Feb and May 2024, Jan 2026. |
| `accuracy` (falsely low) | Monitor shows low SpO2 while the real value is normal. | Unnecessary oxygen or interventions. | Medium | (included above) | | |
| `signal_acquisition` | No reading or intermittent reading during monitoring. | Monitoring gap; usually noticed by staff. | Medium | 581 | 9 / 27 | None strong. |
| `power_battery` | Device shuts down during transport or monitoring. | Monitoring gap. | Medium | 1,986 | 15 / 17 | Step change in 2023, one manufacturer group; confirmed by FDA terms. |
| `display` | Missing segments make a value misread (e.g. 98 read as 90). | Wrong decision from a misread value. | Medium | 2,217 | 13 / 34 | None. |
| `patient_contact` | Sensor causes heat, pressure or skin damage, for example on neonatal skin. | Burns, blisters, pressure injury. | Medium (author's decision, see note) | 822 | 3 / 263 | Sustained rise during 2023 across several manufacturers; only visible with this taxonomy. |
| `software_behavior` | Unexpected reset, self-cycling or wrong message during use. | Monitoring gap; confusion. | Low–Medium | 196 | 9 / 2 | Jul 2023, May 2026 (unreliable: low recall). |
| `physical_damage` | Broken housing or cable, exposed wires. | Device unusable; possible electrical or skin hazard. | Low–Medium | 251 | 4 / 4 | None. |
| no keyword match | – | – | – | 3,147 | 88 / 98 | Not charted. |

The model cannot tell falsely high from falsely low readings, so both `accuracy` rows share one count.

**Note on `patient_contact`:** the author rated it Medium because the harm is direct, visible, and in most reports reversible. The labeled sample also contains severe cases (a burn in a baby that needed plastic surgery; full-thickness burns after a sensor was left on during an MRI; stage II pressure ulcers and deep tissue injury). These are recorded as exceptions to watch, and the rating should be revisited if their share grows. With the scale above, a reviewer could argue for High; the decision and its reason are kept visible on purpose.

## Observations for the review
1. **Alarm problems dominate the reports coded as Death** (187 of the 361 described Death reports). This matches the engineering view that a silent alarm failure is the most dangerous failure mode of a monitor. About a third of these narratives (66 of 187, keyword search for terms such as "unresponsive", "found deceased" or "expired") describe a patient found in that state, with incomplete information about what the device did, so causality cannot be assessed.
2. **Patient-contact reports carry most of the injury reports** (263), and their share rose in 2023 across several manufacturers. In a real review this would trigger reading those reports, checking sensor changes or new products in that period, and checking whether use errors (sensor not moved, left on during MRI) dominate.
3. **Two signals are confirmed by two independent codings** (alarm in late 2025, shutdowns in 2023), each concentrated in one manufacturer. A real review would check recalls and corrective actions for those periods and whether complaint coding changed.
4. **Falsely high readings need separate tracking** from falsely low ones, because they hide hypoxemia. FDA's draft guidance of 7 January 2025 on pulse oximeters was motivated in part by accuracy differences across skin pigmentation (see `README.md` in this folder). MAUDE narratives rarely mention skin pigmentation, so this data **cannot** assess that issue.

## What a real review would add (and this project cannot)
- Units in the field, to estimate probability of occurrence.
- The manufacturer's complaint files and investigation results (root causes).
- Risk acceptability criteria defined in a risk management plan.
- Verification that existing risk controls are still effective.

## Appendix: earlier estimate with FDA problem terms
Before the classifier existed, each category was approximated by groups of FDA problem terms. Reports (Death / Injury): alarm 2,193 (134 / 53); accuracy 3,910 (57 / 99); signal_acquisition 970 (14 / 50); power_battery 1,770 (12 / 10); display 2,217 (13 / 35); patient_contact 421 (1 / 122); software_behavior 502 (9 / 5); physical_damage 304 (0 / 3). Term groups: alarm = Device Alarm System, No Audible Alarm, No Audible Prompt/Feedback; accuracy = Incorrect Measurement, Low Readings, High Readings, Incorrect, Inadequate or Imprecise Result or Readings, False Reading From Device Non-Compliance; signal_acquisition = Sensing Intermittently, Unable to Obtain Readings, Failure to Analyze Signal, Device Sensing Problem, Failure to Read Input Signal; power_battery = Unexpected Shutdown, Battery Problem, Failure To Run On AC/DC, Failure to Power Up, Failure to Charge, Power Problem, Low Battery, Charging Problem, Premature Discharge of Battery, Loss of Power; display = Display or Visual Feedback Problem, No Display/Image, Image Display Error/Artifact, Erratic or Intermittent Display, Component Missing; patient_contact = Patient-Device Incompatibility, Patient Device Interaction Problem, Temperature Problem; software_behavior = Inappropriate or Unexpected Reset, Device Displays Incorrect Message, Communication or Transmission Problem; physical_damage = Break, Crack, Corroded.

The two codings agree on the ranking of harm: alarm for deaths, patient contact for injuries.

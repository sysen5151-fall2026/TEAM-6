# Emission factor review record

Requirement 2.4.1 and component requirement 5.4.1 ask for reviewed factors with source, units, geography, methodology and version. This file is the review record for factor set `epa-hub-2025-01` (`src/c0_2_reference_data/published_factors.py`).

| Field | Value |
|---|---|
| Factor set | `epa-hub-2025-01` |
| Source | EPA GHG Emission Factors Hub, Last Modified 15 January 2025, Table 10 (Scope 3 Category 6 and 7) and Table 11 (GWP, IPCC AR5): https://www.epa.gov/system/files/documents/2025-01/ghg-emission-factors-hub-2025.pdf |
| Values reviewed | Passenger car 0.297 kg CO2, 0.0059 g CH4, 0.0053 g N2O per vehicle-mile; bus 0.066 kg CO2, 0.0046 g CH4, 0.0019 g N2O per passenger-mile; GWP CH4 28, N2O 265 |
| Result in the product | drive 185.523 g CO2e per vehicle-km; bus 41.403 g CO2e per passenger-km; walk 0 and bike 0 (assumption: no fuel burned, not an EPA table value) |
| Scope and limits | Tailpipe (tank-to-wheel) only, no upstream emissions; US geography; scooter and carpool are not covered by the EPA table and keep the labelled placeholder of the Data Adapter (C.3) |
| Reviewer | Yinping Yin, Sustainability Data and Analysis Lead (Method Reviewer, SH.4) |
| Review date | 2026-11-09 |
| Decision | Approved, as reported by Luyu Chen after Yinping Yin approved the values and conversion in person. |
| Reviewer's own confirmation | Initials and date, written by the reviewer: ____________ (or a commit by Yinping Yin that adds this line) |
| Conditions | Re-review when the hub publishes a new edition, when a scooter or carpool factor is added, or when upstream emissions are included. |

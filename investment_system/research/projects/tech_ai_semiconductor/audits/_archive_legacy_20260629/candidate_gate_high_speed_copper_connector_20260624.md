# Candidate Gate - high_speed_copper_connector - 20260624

Status: PASS
ERROR: 0
WARNING: 0
INFO: 10
Recommendation: enter Publish Gate

## Checks
- PASS: sector card structure matches candidate output spec sections - required candidate sections present
- PASS: source_id traceability - referenced source_ids resolve to bound evidence files
- PASS: evidence_id traceability - referenced evidence_ids resolve to bound evidence files
- PASS: no missing evidence converted into deterministic conclusion - missing/order/customer/certification gaps remain explicit
- PASS: no investment advice / target price / position sizing - forbidden investment-action terms absent
- PASS: no formal score or A/B/C/D/E rating - score_status remains NOT_RATED and formal_score not_enabled
- PASS: risk / missing / conflict / counter-evidence sections exist - required caution sections present
- PASS: new industry evidence correctly classified - new evidence levels: {'EV-HSCC-PRODUCT-300563-20260624': 'strong', 'EV-HSCC-FINSEG-300563-20260624': 'strong', 'EV-HSCC-PRODUCT-300913-20260624': 'strong', 'EV-HSCC-VALIDATION-CAPACITY-300913-20260624': 'strong', 'EV-HSCC-FINSEG-300913-20260624': 'strong', 'EV-HSCC-PRODUCT-605277-20260624': 'strong', 'EV-HSCC-VALIDATION-605277-20260624': 'strong', 'EV-HSCC-FINSEG-605277-20260624': 'strong'}
- PASS: validate_outputs passed - validate_outputs exit_code=0
- PASS: publish boundary respected - candidate remains in audit/formal_candidate_outputs only

## Traceability
- referenced_source_ids: 8
- referenced_evidence_ids: 24
- unresolved_source_ids: none
- unresolved_evidence_ids: none

## Bound Evidence Files
- investment_system/research/evidence/high_speed_copper_connector.yaml
- investment_system/research/evidence/trading_heat_high_speed_copper_connector.yaml
- investment_system/research/evidence/high_speed_copper_connector_product_validation.yaml

## Boundary
- formal output directory write: no
- gated formal generated: no
- release manifest generated: no
- formal score/rating generated: no
- investment advice generated: no

## Remaining Missing Evidence
- named customer contracts, order amounts, certification files, and model-level revenue split remain missing for parts of the stock pool.
- Shenyu still lacks named AI-server customer/order evidence, although annual-report product evidence is now strong.

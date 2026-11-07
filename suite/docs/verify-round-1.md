# verify round 1

- 时间：2026-11-06 21:10:30
- 用时：50.4s
- 结论：**全绿 PASS**

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| clean-state | PASS | `{"logs": 1, "runs": 2, "pycache": 10}` |
| build-assets | PASS | `{"returncode": 0, "tail": "{\"ok\": true, \"elapsed_s\": 0.87, \"stats\": {\"pointCount\": 9224, \"featureCount\": 94992, \"icons\": 37, \"markerTypes\": 291, \"templates\": 9}}", "stderr": ""}` |
| compileall | PASS | `{"returncode": 0, "tail": "compiled-first-party bad=0"}` |
| assets-verify | PASS | `{"ok": true, "hashesChecked": 10, "hashesFailed": 0, "points": 9224, "mmapSeconds": 0.0004, "canonicalMap": true, "nrc": {"pokemon": 461, "skill": 491, "pokemon_skill": 20433}}` |
| engines-verify | PASS | `{"ok": 36, "failed": 0, "total": 36, "failedEntries": [], "components": {"total": 55, "ready": 44, "notWired": 6, "skipped": 1, "blockedVendor": 4, "missingDeps": 0, "implemented": 44}, "componentCountExpected": 55, "entryCount": 36}` |
| requirements-lock | PASS | `{"capture": {"match": true, "packages": 3}, "vision": {"match": true, "packages": 7}, "input": {"match": true, "packages": 4}, "sift": {"match": true, "packages": 3}, "battle": {"match": true, "packages": 14}, "scheduler": {"match": true, "packages": 19}, "vendor": {"match": true, "packages": 0}}` |
| three-chains | PASS | `{"sift": {"status": "ok", "action": "locate", "hasResult": true, "error": null}, "capture": {"status": "ok", "action": "capture", "hasResult": true, "error": null}, "battle": {"status": "ok", "action": "responder", "hasResult": true, "error": null}}` |
| frontend-probes | PASS | `{"8787": 200, "8788": 200, "8800": 200, "5173": 200, "statsTotal": 55, "expectedTotal": 55, "vendorGroup": true, "vendorComponents": 16}` |
| supervisor-restart | PASS | `{"restartSeconds": 0.863, "restartReady": [true], "restartEvents": 1, "otherEnginesUntouched": true, "seqContiguous": true, "tsMonotonic": true, "manifestPackages": {"kernel": 0, "capture": 0, "vision": 0, "input": 0, "sift": 0, "battle": 0, "scheduler": 0, "vendor": 0}, "manifestSnapshotBytes": 942}` |
| frontend-latest-run | PASS | `{"latestRun": "verify-restart", "overviewCurrent": "verify-restart", "engines": ["kernel", "capture", "vision", "input", "sift", "battle", "scheduler", "vendor"], "vendorComponents": ["vendor.rocopilot", "vendor.auto_rocokingdom", "vendor.luoke_location", "vendor.roco_map_tracker", "vendor.autocapture", "vendor.game_automation", "vendor.nrc_ai", "vendor.adolph_rules", "vendor.balance_lab", "vendor.pets_gen", "vendor.sift_map_tracker", "vendor.interception", "vendor.bettergi", "vendor.yotta", "vendor.rocokingdom_ui", "vendor.rocotools"], "count": 55}` |

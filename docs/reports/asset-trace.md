# 资产追溯报告

清单：`scripts/assets/manifest.json`（34 条）

| 资产 | 类型 | 可获取 | 依据 |
| --- | --- | --- | --- |
| `vendor/Adolph321-Adolph` | git-repo | 是 | HTTP 200 |
| `vendor/ColinHong10-NRC_AI` | git-repo | 是 | HTTP 200 |
| `vendor/ElliottZhao666666-rocom-codex-pets-gen` | git-repo | 是 | HTTP 200 |
| `vendor/Makapic-RocoPilot` | git-repo | 是 | HTTP 200 |
| `vendor/Pacific-shark-roco-balance-lab` | git-repo | 是 | HTTP 200 |
| `vendor/SCH-CMYK-game-automation` | git-repo | 是 | HTTP 200 |
| `vendor/Tsuann-RocoKingdom-AutoCapture` | git-repo | 是 | HTTP 200 |
| `vendor/Wooziii-roco-map-tracker` | git-repo | 是 | HTTP 200 |
| `vendor/babalae-better-genshin-impact` | git-repo | 是 | HTTP 200 |
| `vendor/eachyczhang-RocoTools` | git-repo | 是 | HTTP 200 |
| `vendor/oblitum-Interception` | git-repo | 是 | HTTP 200 |
| `vendor/rookie-orange-rocokingdom-ui` | git-repo | 是 | HTTP 200 |
| `vendor/yorusacri-Auto-rocokingdom` | git-repo | 是 | HTTP 200 |
| `vendor/yottaapp-yotta` | git-repo | 是 | HTTP 200 |
| `vendor/zh19990906-luoke_location` | git-repo | 是 | HTTP 200 |
| `archive/sift-map-tracker` | rights-excluded | 排除 | 第三方素材，按策略永久排除 |
| `datasets/models/upstream/sprite_detector.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/geli.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/huolong.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/youyingshu.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/xueren.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/yolo26s.pt` | repo-file | 是 | HTTP 200 |
| `datasets/models/upstream/best_20260601.pt` | local-only | 排除 | 来自只发二进制的发布包，没有公开源；本地副本是唯一来源 |
| `datasets/models/upstream/loftr_model.onnx` | local-only | 排除 | 来自只发二进制的发布包，没有公开源；本地副本是唯一来源 |
| `datasets/models/upstream/SIFT_features.npz` | local-only | 排除 | 来自只发二进制的发布包，没有公开源；本地副本是唯一来源 |
| `datasets/models/upstream/item_siamese_v2.onnx` | local-only | 排除 | 来自只发二进制的发布包，没有公开源；本地副本是唯一来源 |
| `datasets/models/upstream/SIFT_features*.npz` | local-only | 排除 | 来自只发二进制的发布包，没有公开源；本地副本是唯一来源 |
| `archive/release` | built-artifact | 是 | python scripts/package-release.py --all（脚本 scripts/package-release.py 在） |
| `release/` | built-artifact | 是 | python scripts/package-release.py --mode lite（脚本 scripts/package-release.py 在） |
| `docs/screenshots` | built-artifact | 是 | node scripts/verify/make-shots.mjs（脚本 scripts/verify/make-shots.mjs 在） |
| `webui` | generated | 是 | webui/index.html 静态文件，无构建步骤；server.py 直接托管（脚本 webui/index.html 在） |
| `datasets/map/icons` | rights-excluded | 排除 | 第三方素材，按策略永久排除 |
| `datasets/bwiki/*.db` | rights-excluded | 排除 | 第三方素材，按策略永久排除 |
| `datasets/pvp/*.db` | rights-excluded | 排除 | 第三方素材，按策略永久排除 |

合计：可获取 25，不可获取 0，排除 9。

# GitHub 发布步骤

以下步骤假设源码目录为 `quality-compliance`，并且你已经在 GitHub 创建了空仓库。命令中的路径请替换成实际路径。

## 1. 整理公开仓库目录

只复制 skill 的公开文件，不复制运行数据和宿主项目的其他目录：

```bash
mkdir quality-compliance-public
rsync -a --exclude '.DS_Store' --exclude '__pycache__' --exclude '*.pyc' \
  quality-compliance/SKILL.md \
  quality-compliance/manifest.json \
  quality-compliance/agents \
  quality-compliance/data \
  quality-compliance/references \
  quality-compliance/scripts \
  quality-compliance-public/
```

把本发布材料中的 `README.md`、`DISCLAIMER.md`、`CONTRIBUTING.md`、`SECURITY.md`、`RELEASE_CHECKLIST.md`、`.github/` 和来源登记模板复制到公开仓库根目录。

## 2. 完成发布前决策

编辑 `manifest.json` 中的 `distribution.license`，加入正式的 `LICENSE` 和 `NOTICE`。在法规内容完成合格审核前，保留：

```json
"public_release_ready": false,
"regulatory_content": {"status": "draft-requires-qualified-review"}
```

第一版建议发布为 `alpha` 或 `controlled-pilot`，而不是正式合规产品。

## 3. 本地验证和打包

```bash
cd quality-compliance-public
find . -name '.DS_Store' -o -name '*.pyc' -o -name '__pycache__'
python3 scripts/validate_release.py
python3 scripts/build_release.py --output-dir dist
```

如果校验提示 `.DS_Store`，删除该文件后重新运行。当前候选包已知会因源码目录中的 `.DS_Store` 失败。

## 4. 初始化 Git 并提交

```bash
git init -b main
git add .
git diff --cached --check
git commit -m "chore: publish quality-compliance alpha"
git remote add origin git@github.com:<OWNER>/<REPO>.git
git push -u origin main
```

## 5. 创建预发布版本

```bash
git tag -a v0.1.0-alpha.1 -m "quality-compliance v0.1.0-alpha.1"
git push origin v0.1.0-alpha.1
```

在 GitHub Releases 中选择该 tag，勾选 pre-release，填写变更说明，并上传：

- `dist/quality-compliance-core-<version>.zip`
- `dist/quality-compliance-core-<version>.zip.sha256`

## 6. 仓库设置

- 开启 Issues 和 Discussions；
- 对 `main` 开启至少一名维护者审查；
- 配置 `SECURITY.md` 对应的私密安全联系方式；
- 启用 Dependabot 或定期依赖/运行环境检查；
- 在 About 中添加 `medical-devices`、`quality-management`、`china`、`gsp`、`codex-skill` 等主题；
- 发布后用一个全新目录完成安装和五步 smoke test。

## 7. 后续版本规则

- 代码或 JSON API 兼容变更：遵循 SemVer；
- 法规来源、任务判断或适用范围变化：至少增加次版本号，并在 release notes 中写明来源和审核日期；
- 每次法规内容更新都保留来源登记和变更记录；
- 任何从“草稿待核验”变为“已核验”的状态，都必须有合格审核记录支撑。


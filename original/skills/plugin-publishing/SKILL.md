# Plugin Publishing Skill

本 skill 用于指导如何将本地 skills 打包为 Cowork Plugin 并发布到 GitHub marketplace，使其可被跨项目、跨设备安装复用。

---

## 核心概念

三层结构，自上而下：

- **Marketplace**：一个 GitHub 仓库，包含 `.claude-plugin/marketplace.json`，是 plugin 的目录/索引
- **Plugin**：marketplace 里的一个条目，对应一个目录，包含 `.claude-plugin/plugin.json`
- **Skill**：plugin 里 `skills/` 子目录下的文件夹，每个包含一个 `SKILL.md`

关系：一个 marketplace 可以包含**多个 plugin**，一个 plugin 可以包含**多个 skills**。不需要为不同分类的 skills 开多个 GitHub 仓库。

---

## 方案一：所有 skills 放在一个 plugin 里（简单）

适用于个人 skill 集合，不需要分类管理。

### 目录结构

```
<github-repo>/                       ← marketplace = git repo root
├── .claude-plugin/
│   ├── marketplace.json             ← marketplace 索引
│   └── plugin.json                  ← plugin 清单（source 为 "./" 时必须共存）
├── skills/
│   ├── skill-a/
│   │   └── SKILL.md
│   ├── skill-b/
│   │   └── SKILL.md
│   └── ...
└── .gitignore
```

### marketplace.json

```json
{
  "name": "<marketplace-name>",
  "owner": { "name": "<your-name>" },
  "plugins": [
    {
      "name": "<plugin-name>",
      "description": "描述这个 plugin 包含的 skill 集合",
      "source": "./"
    }
  ]
}
```

### plugin.json

```json
{
  "name": "<plugin-name>",
  "description": "同上描述",
  "version": "1.0.0"
}
```

**注意**：当 `source` 为 `"./"` 时，repo 根目录本身就是 plugin，`marketplace.json` 和 `plugin.json` 必须同时存在于 `.claude-plugin/` 目录下。

---

## 方案二：按分类拆成多个 plugin（推荐长期使用）

适用于 skills 数量较多，需要让用户按需安装。

### 目录结构

```
<github-repo>/
├── .claude-plugin/
│   └── marketplace.json
├── writing-tools/                   ← plugin 1
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── ml-paper-writing/
│       ├── humanizer/
│       └── humanizer-zh/
├── presentation-tools/              ← plugin 2
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── scientific-slides/
│       ├── latex-posters/
│       └── ppt-generator/
├── dev-tools/                       ← plugin 3
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── skills/
│       ├── langchain-architecture/
│       ├── langgraph/
│       └── claude-d3js-skill/
└── .gitignore
```

### marketplace.json

```json
{
  "name": "<marketplace-name>",
  "owner": { "name": "<your-name>" },
  "plugins": [
    {
      "name": "writing-tools",
      "source": "./writing-tools",
      "description": "ML 论文写作、文本人性化"
    },
    {
      "name": "presentation-tools",
      "source": "./presentation-tools",
      "description": "学术 slides、LaTeX 海报"
    },
    {
      "name": "dev-tools",
      "source": "./dev-tools",
      "description": "LangChain/LangGraph 架构、D3.js 可视化"
    }
  ]
}
```

每个 plugin 子目录下的 `plugin.json`：

```json
{
  "name": "writing-tools",
  "description": "ML 论文写作、文本人性化",
  "version": "1.0.0"
}
```

用户可以按需安装：

```bash
/plugin install writing-tools@<marketplace-name>
/plugin install presentation-tools@<marketplace-name>
```

---

## 发布和安装流程

### 发布（一次性）

```bash
# 1. 推送到 GitHub
git add -A && git commit -m "publish as marketplace" && git push

# 仓库可以是 public 或 private（private 需要安装者有 pull 权限）
```

### 安装（使用者执行）

```bash
# 1. 注册 marketplace（用 GitHub 仓库路径，如 Touricks/fanshi_personal_skills）
/plugin marketplace add <github-owner>/<repo-name>

# 2. 安装 plugin（用 marketplace.json 里定义的 name）
/plugin install <plugin-name>@<marketplace-name>

# 3. 可能需要重启 Cowork 会话才能生效
```

### 更新

```bash
# 发布方：修改 skills，更新 plugin.json 里的 version，push
# 使用方：
/plugin marketplace update
```

---

## 常见坑和注意事项

### 命名规范

- `marketplace name` 和 `plugin name` 都必须用 **kebab-case**（小写 + 连字符，不能有空格）
- marketplace name 不能用 Anthropic 保留名：`claude-code-plugins`、`anthropic-plugins`、`agent-skills` 等
- marketplace name 不需要全局唯一，只需在同一用户已注册的 marketplace 中不冲突

### `source: "./"` 的特殊情况

当 marketplace 和 plugin 合并在同一个 repo 根目录时（方案一），`marketplace.json` 和 `plugin.json` 必须**同时**存在于 `.claude-plugin/` 下。漏掉 `plugin.json` 会导致安装后 skills 无法被发现。

### Skills 自动发现

plugin 目录下的 `skills/` 子文件夹会被**自动扫描**，每个包含 `SKILL.md` 的子目录都会被识别为一个 skill。**不需要**在 `marketplace.json` 里手动列出每个 skill 的路径。

### Sandbox 限制

在 Cowork 沙箱环境中，以下操作可能会因权限限制而失败：

- `git mv` / `git add` / `git commit`：沙箱对挂载目录的 `.git/index.lock` 可能没有写权限
- 与 Anthropic 内置 skill 同名的目录（docx、pdf、pptx、xlsx、skill-creator）可能有移动限制

遇到这些情况时，应在**本机终端**执行 git 操作。

### 跨 plugin 文件引用

plugin 安装时会被**复制**到缓存目录，因此不能用 `../` 引用 plugin 目录外的文件。如果多个 plugin 需要共享文件，使用 symlink（安装时会跟随 symlink 复制）。

---

## 快速参考

| 操作 | 命令 |
|------|------|
| 注册 marketplace | `/plugin marketplace add <owner>/<repo>` |
| 安装 plugin | `/plugin install <plugin>@<marketplace>` |
| 更新 marketplace | `/plugin marketplace update` |
| 验证结构 | `/plugin validate .` |
| 查看已安装 | 检查 `~/.claude/plugins/` 或 `installed_plugins.json` |

---

## 参考文档

- [Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Anthropic knowledge-work-plugins (示例)](https://github.com/anthropics/knowledge-work-plugins)
- [Plugin 技术参考](https://code.claude.com/docs/en/plugins-reference)

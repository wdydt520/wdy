# GitHub Marketplace 发布说明

## 发布类型

GitHub Marketplace 支持两种发布方式：

### 方式一：GitHub App（推荐）
- 适合：交互式应用、需要 API 集成的工具
- 流程：创建 GitHub App → 提交审核 → 发布到 Marketplace

### 方式二：GitHub Action
- 适合：自动化工作流工具
- 流程：创建 Action → 发布到 Marketplace

---

## 发布步骤

### 步骤一：创建 GitHub App

1. 访问：https://github.com/settings/apps/new
2. 填写应用信息：

| 字段 | 值 |
|------|-----|
| GitHub App name | TCM 3D Differentiation |
| Description | 中医三维辨证辅助诊断技能 |
| Homepage URL | https://wdydt520.github.io/tcm-3d-differentiation/web/ |
| Setup URL | https://wdydt520.github.io/tcm-3d-differentiation/web/ |
| Webhook | 取消勾选 "Active" |

3. 设置权限：
   - Contents: Read-only

4. 点击 "Create GitHub App"

### 步骤二：提交到 Marketplace

1. 进入你的 App 设置页面
2. 点击 "Marketplace" 标签
3. 点击 "List this app on Marketplace"
4. 填写定价信息：
   - 选择 "Free"（免费）
5. 填写 Listing 信息：
   - Name: TCM 3D Differentiation
   - Short description: 中医三维辨证辅助诊断系统
   - Detailed description: 见下方
   - Categories: Developer tools, Education
6. 提交审核

---

## Listing 描述内容

### Short Description (最多 120 字符)

```
中医三维辨证辅助诊断系统 - 基于「五气-脏腑-邪留」框架，101证候、133方剂
```

### Detailed Description

```markdown
# 中医三维辨证辅助诊断系统

基于**欧阳锜《证病结合用药式》**「五气-脏腑-邪留」三维辨证框架的临床决策支持系统。

## 核心特点

- **三维辨证框架**：五气（病因）+ 脏腑（病位）+ 邪留（病理产物）
- **纲-目结构**：明确主次，指导治疗
- **101个证候**：五气为病41证 + 脏腑主病45证 + 邪留发病15证
- **133首方剂**：含组成、功效、加减、注意事项
- **4090条疾病应用**：各疾病辨证要点与方药加减

## 辨证流程

```
步骤一：信息采集 → 收集症状、体征
步骤二：三维归因 → 五气 + 脏腑 + 邪留
步骤三：分析关系 → 判断因果链、主次关系
步骤四：确定证型 → 纲-目结构命名
步骤五：指导治疗 → 方药建议
```

## 数据库统计

| 数据类型 | 数量 |
|----------|------|
| 症状 | 76 个 |
| 证候 | 101 个 |
| 方剂 | 133 首 |
| 疾病应用 | 4090 条 |

## 使用场景

- 临床辨证辅助诊断
- 中医证候与方药推荐
- 症状分析与证候匹配
- 三维纲目辨证分析
- 中医教学与学习

## 理论来源

本技能基于国医大师**欧阳锜**先生所著《证病结合用药式》的三型辨证体系。

## 注意事项

本系统为辅助诊断工具，不能替代医生临床判断。
```

---

## 审核周期

- GitHub 审核时间：通常 3-7 个工作日
- 审核标准：
  - 功能完整可用
  - 描述准确清晰
  - 符合 Marketplace 政策

---

## 替代方案

如果 GitHub App 流程复杂，可考虑：

### 1. 发布为开源项目
- 已完成：https://github.com/wdydt520/tcm-3d-differentiation
- 可被其他 AI 工具集成使用

### 2. 发布到 npm / PyPI
- 作为可安装的包发布
- 更易被开发者使用

---

## 当前仓库链接

- **GitHub 仓库**：https://github.com/wdydt520/tcm-3d-differentiation
- **GitHub Pages**：https://wdydt520.github.io/tcm-3d-differentiation/web/

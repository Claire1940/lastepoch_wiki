# SEO 完整配置指南

本文档详细说明如何检查和配置项目的 SEO 设置，确保网站在搜索引擎中获得最佳表现。

## 目录

1. [SEO 配置位置](#seo-配置位置)
2. [检查清单](#检查清单)
3. [配置步骤](#配置步骤)
4. [测试验证](#测试验证)
5. [常见问题](#常见问题)

---

## SEO 配置位置

### 1. 主布局文件 - `src/app/[locale]/layout.tsx`

这是 SEO 的核心配置文件，包含 `generateMetadata` 函数（第 34-96 行）：

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.lucidblocks.wiki'
  const t = await getTranslations('seo.home')

  return {
    title: t('title'),
    description: t('description'),
    keywords: keywords,
    robots: { ... },
    openGraph: { ... },
    twitter: { ... },
    icons: { ... },
    manifest: '/manifest.json',
    alternates: buildLanguageAlternates(...)
  }
}
```

**配置内容：**
- 页面标题 (title)
- 描述 (description)
- 关键词 (keywords)
- 爬虫规则 (robots)
- Open Graph 社交分享卡片
- Twitter Card 配置
- 网站图标 (favicon)
- 多语言链接 (alternates)

### 2. 翻译文件 - `src/locales/*.json`

所有 SEO 文本内容存储在翻译文件的 `seo` 节点下：

```json
{
  "seo": {
    "home": {
      "title": "Lucid Blocks Wiki - Guides & Tips",
      "description": "Lucid Blocks Wiki with guides, tips...",
      "keywords": "Lucid Blocks, Roblox, guides, tips...",
      "ogTitle": "Lucid Blocks Wiki - Guides & Tips",
      "ogDescription": "Complete Lucid Blocks resource hub!...",
      "twitterTitle": "Lucid Blocks Wiki - Guides & Tips",
      "twitterDescription": "Complete Lucid Blocks resource hub!..."
    }
  }
}
```

**需要配置的语言文件：**
- `src/locales/en.json` - 英文
- `src/locales/zh.json` - 中文
- `src/locales/es.json` - 西班牙语
- `src/locales/fr.json` - 法语
- `src/locales/pt.json` - 葡萄牙语
- `src/locales/ru.json` - 俄语
- `src/locales/th.json` - 泰语
- `src/locales/tr.json` - 土耳其语
- `src/locales/vi.json` - 越南语
- `src/locales/de.json` - 德语
- `src/locales/ja.json` - 日语

### 3. 动态内容页面 - `src/app/[locale]/[...slug]/page.tsx`

为动态内容（如文章、指南）生成 SEO 元数据（第 205 行起）：

```typescript
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { locale, slug } = await params
  const contentType = slug[0]

  // 列表页元数据
  if (isListPage) {
    const t = await getTranslations(`pages.${contentType}`)
    return {
      title: t('metaTitle'),
      description: t('metaDescription'),
      alternates: buildLanguageAlternates(...),
      openGraph: { ... },
      robots: { ... }
    }
  }

  // 详情页元数据（从 MDX frontmatter 读取）
  return {
    title: article.frontmatter.title,
    description: article.frontmatter.description,
    ...
  }
}
```

### 4. 静态页面

以下页面都有独立的 `generateMetadata` 函数：
- `src/app/[locale]/about/page.tsx` - 关于页面
- `src/app/[locale]/privacy-policy/page.tsx` - 隐私政策
- `src/app/[locale]/terms-of-service/page.tsx` - 服务条款
- `src/app/[locale]/copyright/page.tsx` - 版权页面

### 5. Sitemap - `src/app/sitemap.ts`

自动生成 XML sitemap，包含：
- 首页（所有语言）
- 静态页面（所有语言）
- 所有 MDX 文章（所有语言和内容类型）

**配置项：**
- `priority` - 页面优先级（0.0-1.0）
- `changeFrequency` - 更新频率（daily/weekly/monthly/yearly）
- `lastModified` - 最后修改时间

### 6. 工具函数 - `src/lib/i18n-utils.ts`

`buildLanguageAlternates` 函数用于生成多语言链接：

```typescript
export function buildLanguageAlternates(path: string, locale: Locale, baseUrl: string) {
  return {
    canonical: '...',  // 规范链接
    languages: {       // 所有语言版本
      'en': '...',
      'zh': '...',
      'x-default': '...'
    }
  }
}
```

---

## 检查清单

### ✅ 基础 SEO

- [ ] **网站 URL** - 确认 `NEXT_PUBLIC_SITE_URL` 环境变量已设置
- [ ] **页面标题** - 每个页面都有唯一的 title（50-60 字符）
- [ ] **描述** - 每个页面都有 description（150-160 字符）
- [ ] **关键词** - 设置相关关键词（5-10 个）
- [ ] **Robots** - 配置爬虫索引规则

### ✅ Open Graph (社交分享)

- [ ] **OG 图片** - 确认 `/public/og-image.jpg` 存在（1200x630px）
- [ ] **OG 标题** - 设置 `ogTitle`（与 title 可以不同）
- [ ] **OG 描述** - 设置 `ogDescription`
- [ ] **OG 类型** - 设置为 `website`
- [ ] **OG URL** - 自动生成，检查是否正确

### ✅ Twitter Card

- [ ] **Card 类型** - 设置为 `summary_large_image`
- [ ] **Twitter 标题** - 设置 `twitterTitle`
- [ ] **Twitter 描述** - 设置 `twitterDescription`
- [ ] **Twitter 图片** - 使用与 OG 相同的图片
- [ ] **Twitter 创建者** - 设置 `creator` 账号

### ✅ 网站图标

- [ ] **favicon.ico** - 根目录图标
- [ ] **favicon-16x16.png** - 16x16 图标
- [ ] **favicon-32x32.png** - 32x32 图标
- [ ] **apple-touch-icon.png** - 180x180 苹果图标
- [ ] **manifest.json** - PWA 配置文件

### ✅ 多语言 SEO

- [ ] **hreflang 标签** - 通过 `alternates.languages` 自动生成
- [ ] **Canonical 链接** - 通过 `alternates.canonical` 自动生成
- [ ] **x-default** - 设置默认语言版本
- [ ] **所有语言翻译** - 确保每种语言都有 `seo` 节点

### ✅ Sitemap

- [ ] **sitemap.xml** - 访问 `/sitemap.xml` 检查是否生成
- [ ] **所有页面** - 确认所有重要页面都在 sitemap 中
- [ ] **优先级** - 检查页面优先级设置是否合理
- [ ] **更新频率** - 检查 changeFrequency 是否准确

### ✅ 结构化数据

- [ ] **JSON-LD** - 检查是否有结构化数据（如 Article, BreadcrumbList）
- [ ] **Schema.org** - 使用正确的 schema 类型

---

## 配置步骤

### 步骤 1: 配置环境变量

在 `.env.local` 中设置：

```bash
NEXT_PUBLIC_SITE_URL=https://www.bizarrelineage.wiki
```

### 步骤 2: 准备 OG 图片

1. 创建 1200x630px 的图片
2. 保存为 `public/og-image.jpg`
3. 确保文件大小 < 1MB

### 步骤 3: 配置首页 SEO

编辑 `src/locales/en.json`（以及其他语言文件）：

```json
{
  "seo": {
    "home": {
      "title": "你的网站标题 - 主要关键词",
      "description": "150-160 字符的描述，包含主要关键词",
      "keywords": "关键词1, 关键词2, 关键词3, 关键词4, 关键词5",
      "ogTitle": "社交分享标题（可以更吸引人）",
      "ogDescription": "社交分享描述（可以更简短）",
      "twitterTitle": "Twitter 分享标题",
      "twitterDescription": "Twitter 分享描述"
    }
  }
}
```

**注意事项：**
- `title` 应包含品牌名和主要关键词
- `description` 应自然地包含关键词，避免堆砌
- `keywords` 用逗号分隔，5-10 个为宜
- `ogTitle` 和 `twitterTitle` 可以更简短、更吸引人

### 步骤 4: 配置内容页面 SEO

在 MDX 文件的 frontmatter 中添加：

```yaml
---
title: "文章标题"
description: "文章描述"
date: "2026-03-03"
author: "作者名"
tags: ["标签1", "标签2"]
---
```

### 步骤 5: 配置静态页面 SEO

编辑翻译文件中的 `pages` 节点：

```json
{
  "pages": {
    "about": {
      "metaTitle": "About - Lucid Blocks Wiki",
      "metaDescription": "Learn about Lucid Blocks Wiki..."
    },
    "codes": {
      "metaTitle": "Codes - Lucid Blocks Wiki",
      "metaDescription": "All active codes for Lucid Blocks..."
    }
  }
}
```

### 步骤 6: 配置 Sitemap 优先级

编辑 `src/app/sitemap.ts`：

```typescript
// 内容类型优先级配置
const contentTypePriority: Record<string, number> = {
  'codes': 0.9,        // 高优先级
  'tier-list': 0.9,
  'units': 0.8,
  'guide': 0.8,
  'farming': 0.7,
  'gameplay': 0.7,
  'resources': 0.6,
  'community': 0.5,    // 低优先级
}

// 内容更新频率配置
const contentTypeChangeFrequency: Record<string, 'daily' | 'weekly' | 'monthly'> = {
  'codes': 'daily',    // 每天更新
  'tier-list': 'weekly',
  'units': 'weekly',
  'guide': 'weekly',
  'farming': 'weekly',
  'gameplay': 'monthly',
  'resources': 'monthly',
  'community': 'monthly',
}
```

### 步骤 7: 配置 Robots.txt

创建 `public/robots.txt`：

```txt
User-agent: *
Allow: /

Sitemap: https://www.bizarrelineage.wiki/sitemap.xml
```

---

## 测试验证

### 1. 本地测试

```bash
# 构建生产版本
bun run build

# 启动生产服务器
bun start

# 访问以下 URL 检查
http://localhost:3000
http://localhost:3000/sitemap.xml
```

### 2. 检查页面源代码

在浏览器中右键 → 查看网页源代码，检查：

```html
<!-- 基础 Meta -->
<title>Lucid Blocks Wiki - Guides & Tips</title>
<meta name="description" content="...">
<meta name="keywords" content="...">

<!-- Open Graph -->
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:image" content="...">
<meta property="og:url" content="...">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="...">
<meta name="twitter:description" content="...">
<meta name="twitter:image" content="...">

<!-- 多语言 -->
<link rel="canonical" href="...">
<link rel="alternate" hreflang="en" href="...">
<link rel="alternate" hreflang="zh" href="...">
<link rel="alternate" hreflang="x-default" href="...">
```

### 3. 使用在线工具

**Open Graph 测试：**
- Facebook Sharing Debugger: https://developers.facebook.com/tools/debug/
- LinkedIn Post Inspector: https://www.linkedin.com/post-inspector/

**Twitter Card 测试：**
- Twitter Card Validator: https://cards-dev.twitter.com/validator

**结构化数据测试：**
- Google Rich Results Test: https://search.google.com/test/rich-results
- Schema.org Validator: https://validator.schema.org/

**SEO 综合测试：**
- Google Search Console
- Bing Webmaster Tools
- Ahrefs Site Audit
- SEMrush Site Audit

### 4. 检查 Sitemap

访问 `/sitemap.xml`，确认：
- 所有重要页面都包含在内
- URL 格式正确
- 优先级和更新频率合理
- 最后修改时间准确

### 5. 移动端测试

使用 Google Mobile-Friendly Test：
https://search.google.com/test/mobile-friendly

---

## 常见问题

### Q1: 为什么 OG 图片不显示？

**可能原因：**
1. 图片路径错误
2. 图片尺寸不符合要求（应为 1200x630px）
3. 图片文件过大（应 < 1MB）
4. 缓存问题

**解决方法：**
```typescript
// 确保图片 URL 是绝对路径
images: [
  {
    url: `${siteUrl}/og-image.jpg`,  // 使用完整 URL
    width: 1200,
    height: 630,
    alt: '...',
  },
]
```

### Q2: 如何为不同页面设置不同的 OG 图片？

在 MDX frontmatter 中添加：

```yaml
---
title: "文章标题"
ogImage: "/images/article-og.jpg"
---
```

然后在 `generateMetadata` 中读取：

```typescript
openGraph: {
  images: [
    {
      url: article.frontmatter.ogImage
        ? `${siteUrl}${article.frontmatter.ogImage}`
        : `${siteUrl}/og-image.jpg`,
      ...
    }
  ]
}
```

### Q3: 多语言 SEO 如何确保正确？

**检查要点：**
1. 每种语言都有独立的 `seo` 节点
2. `alternates.languages` 包含所有语言版本
3. `x-default` 指向默认语言（通常是英文）
4. URL 结构一致（如 `/en/codes`, `/zh/codes`）

### Q4: 如何提高 SEO 排名？

**关键因素：**
1. **内容质量** - 原创、有价值的内容
2. **关键词优化** - 自然地使用目标关键词
3. **页面速度** - 优化图片、使用 CDN
4. **移动友好** - 响应式设计
5. **内部链接** - 合理的站内链接结构
6. **外部链接** - 获取高质量的反向链接
7. **用户体验** - 降低跳出率，提高停留时间
8. **定期更新** - 保持内容新鲜

### Q5: 如何监控 SEO 表现？

**推荐工具：**
1. **Google Search Console** - 监控搜索表现
2. **Google Analytics** - 分析流量来源
3. **Ahrefs** - 关键词排名和反向链接
4. **SEMrush** - 竞争对手分析
5. **Screaming Frog** - 网站爬取和审计

**关键指标：**
- 自然搜索流量
- 关键词排名
- 点击率 (CTR)
- 跳出率
- 平均停留时间
- 页面加载速度

### Q6: 如何添加结构化数据？

在页面组件中添加 JSON-LD：

```typescript
export default function ArticlePage({ article }) {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": article.title,
    "description": article.description,
    "author": {
      "@type": "Person",
      "name": article.author
    },
    "datePublished": article.date,
    "image": article.image
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      {/* 页面内容 */}
    </>
  )
}
```

---

## 总结

完整的 SEO 配置包括：

1. ✅ 基础 Meta 标签（title, description, keywords）
2. ✅ Open Graph 社交分享配置
3. ✅ Twitter Card 配置
4. ✅ 网站图标和 PWA 配置
5. ✅ 多语言 hreflang 标签
6. ✅ XML Sitemap 生成
7. ✅ Robots.txt 配置
8. ✅ 结构化数据（可选）

**记住：**
- SEO 是长期工作，需要持续优化
- 内容质量比技术优化更重要
- 定期监控和调整策略
- 遵循搜索引擎指南，避免黑帽 SEO

---

**最后更新：** 2026-03-03

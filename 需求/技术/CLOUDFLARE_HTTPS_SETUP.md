# 配置 Cloudflare 和 Dokploy 实现 HTTPS 和 WWW 重定向

## 📋 目录

- [问题描述](#问题描述)
- [解决方案概述](#解决方案概述)
- [第一部分：Cloudflare 配置](#第一部分cloudflare-配置)
- [第二部分：Dokploy 配置](#第二部分dokploy-配置)
- [第三部分：验证配置](#第三部分验证配置)
- [第四部分：Google Search Console 配置](#第四部分google-search-console-配置)
- [配置检查清单](#配置检查清单)
- [架构说明](#架构说明)

---

## 问题描述

### 当前状态

从 Google Search Console 数据显示，网站存在多个版本的 URL 同时被索引：

| URL                               | 状态            | 展示次数 |
| --------------------------------- | --------------- | -------- |
| `http://www.lucidblocks.wiki/`    | ❌ HTTP 版本    | 38 次    |
| `http://lucidblocks.wiki/`        | ❌ HTTP 无 www  | 18 次    |
| `https://www.lucidblocks.wiki/`   | ✅ HTTPS + www  | 11 次    |
| `https://www.lucidblocks.wiki/fr` | ✅ HTTPS 多语言 | -        |

### 根本原因

1. **Dokploy 域名配置问题**：所有域名都配置为 HTTP (Port: 3000)，Cert: none
2. **缺少 HTTP → HTTPS 强制重定向**：用户可以通过 HTTP 访问网站
3. **缺少非 www → www 重定向**：`lucidblocks.wiki` 和 `www.lucidblocks.wiki` 都可以访问
4. **SEO 影响**：
   - 重复内容问题
   - 分散页面权重
   - 降低 SEO 排名

### 技术栈

- **DNS/CDN**: Cloudflare
- **部署平台**: Dokploy（自托管 Docker 部署平台）
- **期望的主域名**: `https://www.lucidblocks.wiki`（HTTPS + www）

### 当前 Dokploy 配置

3 个域名配置：

1. `project1-lucidblocksiki-vbzibg-35e314-43-130-44-149.traefik.me` - HTTP, Port: 3000, Cert: none
2. `lucidblocks.wiki` - HTTP, Port: 3000, Cert: none
3. `www.lucidblocks.wiki` - HTTP, Port: 3000, Cert: none

### 当前环境变量

```bash
NEXT_PUBLIC_SITE_URL=https://www.lucidblocks.wiki ✅ 正确
```

---

## 解决方案概述

### 核心策略

由于使用 Cloudflare + Dokploy 的架构，SSL/TLS 终止应该在 **Cloudflare** 层面完成，而不是在 Dokploy 中配置证书。

### 为什么选择这个方案？

1. ✅ Cloudflare 自动管理 SSL 证书（免费）
2. ✅ 减轻源服务器负担
3. ✅ 更好的性能和安全性
4. ✅ 统一管理所有域名的 SSL

### 配置策略

1. **Cloudflare SSL/TLS 配置** - 在 Cloudflare 和客户端之间使用 HTTPS
2. **Cloudflare → Dokploy 连接** - 可以使用 HTTP（因为在内网/私有连接）
3. **Cloudflare 重定向规则** - 强制 HTTPS 和 www
4. **Dokploy 保持 HTTP** - 无需配置 SSL 证书

---

## 第一部分：Cloudflare 配置

> ⚠️ **重要**：这是主要配置部分，必须完成所有步骤

### 步骤 1：配置 SSL/TLS 加密模式

https://dash.cloudflare.com/610b80b08aa02848902d5fbdafbc9790/home/domains
**路径**: `Cloudflare Dashboard → SSL/TLS → Overview`

**⚠️ 重要：首先检查 Dokploy 域名配置**

在配置 Cloudflare SSL 模式前，先检查 Dokploy 中的域名协议设置：

1. 进入 `Dokploy Dashboard → 你的项目 → Domains` 标签页
2. 查看主域名（如 `yourdomain.wiki` 和 `www.yourdomain.wiki`）的 **Protocol** 字段

**根据 Dokploy 配置选择 SSL 模式**：

#### 情况 A：Dokploy 域名配置为 HTTPS（推荐）✅

如果 Dokploy Domains 显示：

```
Protocol: HTTPS
Port: 3000
Cert: none (Traefik 会自动生成证书)
```

**Cloudflare 配置**：

```
加密模式: Full
```

**说明**：

- `Full` 模式：客户端 ↔ Cloudflare 使用 HTTPS，Cloudflare ↔ Dokploy 也使用 HTTPS
- Dokploy 的 Traefik 会自动处理 SSL 证书（即使显示 "Cert: none"）
- 这是最推荐的配置，避免重定向循环问题

#### 情况 B：Dokploy 域名配置为 HTTP

如果 Dokploy Domains 显示：

```
Protocol: HTTP
Port: 3000
Cert: none
```

**Cloudflare 配置**：

```
加密模式: Flexible
```

**说明**：

- `Flexible` 模式：客户端 ↔ Cloudflare 使用 HTTPS，Cloudflare ↔ Dokploy 使用 HTTP
- 源服务器不需要 SSL 证书
- Cloudflare 会自动处理客户端的 SSL 证书

**⚠️ 常见错误**：

- 如果 Dokploy 配置为 HTTPS，但 Cloudflare 使用 Flexible 模式 → 会导致重定向循环 ❌
- 如果 Dokploy 配置为 HTTP，但 Cloudflare 使用 Full 模式 → 会导致 SSL 错误 ❌

---

### 步骤 2：启用 Always Use HTTPS

**路径**: `Cloudflare Dashboard → SSL/TLS → Edge Certificates`

**配置**:

```
Always Use HTTPS: 开启 (ON)
```

**说明**:

- 自动将所有 HTTP 请求重定向到 HTTPS
- 这会处理：
  - `http://www.lucidblocks.wiki` → `https://www.lucidblocks.wiki`
  - `http://lucidblocks.wiki` → `https://lucidblocks.wiki`

---

### 步骤 3：配置 HSTS（可选但强烈推荐）

**路径**: `Cloudflare Dashboard → SSL/TLS → Edge Certificates`

**配置**:

```
HTTP Strict Transport Security (HSTS): 开启
  - Max Age: 6 months (15768000 seconds)
  - Include subdomains: 开启
  - Preload: 开启
  - No-Sniff Header: 开启
```

**⚠️ 警告**:

- 启用 HSTS 前请确保 HTTPS 已完全配置好
- 启用后浏览器会强制使用 HTTPS，无法轻易回退到 HTTP
- **建议先测试其他配置，确认无误后再启用 HSTS**

---

### 步骤 4：配置非 www → www 重定向规则

**路径**: `Cloudflare Dashboard → Rules → Overview`

**点击**: "Create rule" → 选择 "Redirect Rules"

#### 规则配置（使用 Wildcard Pattern 模式）

**规则名称**:

```
Redirect non-www to www
```

**If incoming requests match...**:

选择 **● Wildcard pattern**（第一个选项）

**Request URL**:

```
https://yourdomain.wiki/*
```

**⚠️ 重要**：

- 必须包含 `https://` 协议前缀
- 必须使用 `/*` 通配符匹配所有路径
- 将 `yourdomain.wiki` 替换为你的实际域名（不带 www）

**Then... → URL redirect**:

```
Type: Static
Target URL: https://www.yourdomain.wiki/${1}
Status code: 301
☑ Preserve query string
```

**⚠️ 关键语法**：

- Target URL 必须使用 `${1}` 占位符（不是 `$1`）
- `${1}` 会自动替换为 `/*` 匹配到的路径部分

**Place at**:

```
Last
```

#### 完整配置示例

以 `lucidblocks.wiki` 为例：

```
Rule name: Redirect non-www to www

If incoming requests match:
  ● Wildcard pattern

Request URL: https://lucidblocks.wiki/*

Then:
  Target URL: https://www.lucidblocks.wiki/${1}
  Status code: 301
  ☑ Preserve query string

Place at: Last
```

**说明**:

- 这会将 `https://lucidblocks.wiki/*` 重定向到 `https://www.lucidblocks.wiki/*`
- 使用 301 永久重定向，告诉搜索引擎这是永久性的改变
- 保留查询参数和路径
- 不会匹配 `www.lucidblocks.wiki`，避免重定向循环

#### 常见错误

❌ **错误 1**：Request URL 缺少 `https://`

```
错误: lucidblocks.wiki/*
正确: https://lucidblocks.wiki/*
```

❌ **错误 2**：Target URL 使用 `$1` 而不是 `${1}`

```
错误: https://www.yourdomain.wiki/$1
正确: https://www.yourdomain.wiki/${1}
```

❌ **错误 3**：Request URL 包含 www（会导致重定向循环）

```
错误: https://www.yourdomain.wiki/*
正确: https://yourdomain.wiki/*
```

---

### 步骤 5：验证 DNS 记录

**路径**: `Cloudflare Dashboard → DNS → Records`

**确认以下记录存在且已代理**:

```
Type: A
Name: www
Target: [Dokploy 服务器 IP 或域名]
Proxy status: Proxied (橙色云朵) ✅

Type: A
Name: @ (或 域名本身)
Target: [Dokploy 服务器 IP 或域名]
Proxy status: Proxied (橙色云朵) ✅
```

**说明**:

- ✅ **橙色云朵**：流量通过 Cloudflare 代理，可以应用重定向规则
- ❌ **灰色云朵**：DNS-only，不会应用 Cloudflare 的规则

---

## 第二部分：Dokploy 配置

### 重要说明

**Dokploy 域名配置取决于你选择的架构**：

#### 推荐配置：Dokploy HTTPS + Cloudflare Full ✅

**Dokploy 域名配置**：

```
Protocol: HTTPS
Port: 3000
Cert: none (Traefik 自动生成)
```

**Cloudflare SSL 模式**：

```
Full
```

**优势**：

- ✅ 端到端加密（客户端 → Cloudflare → Dokploy 都是 HTTPS）
- ✅ 避免重定向循环问题
- ✅ 更高的安全性
- ✅ Traefik 自动管理证书，无需手动配置

#### 备选配置：Dokploy HTTP + Cloudflare Flexible

**Dokploy 域名配置**：

```
Protocol: HTTP
Port: 3000
Cert: none
```

**Cloudflare SSL 模式**：

```
Flexible
```

**说明**：

- ✅ 配置简单，源服务器不需要 SSL
- ⚠️ Cloudflare 到源服务器之间是 HTTP（内网连接）
- ⚠️ 如果 Dokploy 有强制 HTTPS 重定向，会导致循环

### 如何在 Dokploy 中配置域名

1. 进入 `Dokploy Dashboard → 你的项目 → Domains` 标签页
2. 对于每个域名（`yourdomain.wiki` 和 `www.yourdomain.wiki`）：
   - **Path**: `/`
   - **Port**: `3000`
   - **Protocol**: 选择 `HTTPS`（推荐）或 `HTTP`
   - **Cert**: 保持 `none`（Traefik 会自动处理）
3. 点击 "Validate DNS" 验证配置（可选）

### 可选：清理不必要的域名

从配置看到有 3 个域名，建议：

| 域名                                                              | 操作      | 原因                           |
| ----------------------------------------------------------------- | --------- | ------------------------------ |
| `www.lucidblocks.wiki`                                            | ✅ 保留   | 主域名                         |
| `lucidblocks.wiki`                                                | ✅ 保留   | 用于重定向到 www               |
| `project1-lucidblocksiki-vbzibg-35e314-43-130-44-149.traefik.me` | ⚠️ 可删除 | Dokploy 默认域名（如果不需要） |

**如何删除**：

1. 在 Dokploy Dashboard 中，找到该域名配置
2. 点击删除按钮移除

### Next.js 应用配置

环境变量已正确配置：

```bash
NEXT_PUBLIC_SITE_URL=https://www.lucidblocks.wiki ✅
```

✅ 无需修改代码或配置文件

---

## 第三部分：验证配置

### 1. 使用 curl 测试重定向

```bash
# 测试 HTTP www → HTTPS www
curl -I http://www.lucidblocks.wiki
# 期望: 301/308 重定向到 https://www.lucidblocks.wiki

# 测试 HTTP 非 www → HTTPS www
curl -I http://lucidblocks.wiki
# 期望: 301 重定向到 https://www.lucidblocks.wiki

# 测试 HTTPS 非 www → HTTPS www
curl -I https://lucidblocks.wiki
# 期望: 301 重定向到 https://www.lucidblocks.wiki

# 测试最终 URL
curl -I https://www.lucidblocks.wiki
# 期望: 200 OK
```

### 2. 使用浏览器测试

在浏览器中访问以下 URL，确认都重定向到 `https://www.lucidblocks.wiki`：

- ✅ `http://www.lucidblocks.wiki`
- ✅ `http://lucidblocks.wiki`
- ✅ `https://lucidblocks.wiki`

### 3. 使用在线工具验证

使用以下工具验证重定向链：

- https://httpstatus.io/
- https://www.redirect-checker.org/

**期望的重定向链**：

```
http://lucidblocks.wiki
  → 301 → https://lucidblocks.wiki (Cloudflare HTTPS 重定向)
  → 301 → https://www.lucidblocks.wiki (Cloudflare www 重定向)
  → 200 OK
```

### 4. 验证 SSL 证书

```bash
# 检查 SSL 证书
openssl s_client -connect www.lucidblocks.wiki:443 -servername www.lucidblocks.wiki
```

确认证书有效且由 Let's Encrypt 或 Cloudflare 签发。

---

## 第四部分：Google Search Console 配置（可选）

> 💡 **说明**：这部分是可选的 SEO 优化步骤，不影响网站正常访问。如果你不着急做 SEO，可以跳过。

### 操作 1：告诉 Google 你的主域名是哪个

**目的**：让 Google 知道你的网站主域名是 `https://www.yourdomain.wiki`

**怎么做**：

1. 打开 [Google Search Console](https://search.google.com/search-console)
2. 选择你的网站
3. 左侧菜单点击 **"设置"**（最下面）
4. 找到 **"首选域名"** 或 **"Property Settings"**
5. 填写：`https://www.yourdomain.wiki`（带 www 的版本）

### 操作 2：提交网站地图（Sitemap）

**目的**：告诉 Google 你网站有哪些页面

**怎么做**：

1. 在 Google Search Console 左侧菜单找到 **"站点地图"** 或 **"Sitemaps"**
2. 输入：`sitemap.xml`
3. 点击 **"提交"**

**⚠️ 注意**：确保你的 sitemap.xml 文件中所有 URL 都是 `https://www.yourdomain.wiki` 格式（带 www）

### 操作 3：请求 Google 重新抓取首页

**目的**：让 Google 尽快更新你的网站信息

**怎么做**：

1. 在 Google Search Console 顶部搜索框输入：`https://www.yourdomain.wiki`
2. 等待检查完成
3. 点击 **"请求编入索引"** 或 **"Request Indexing"** 按钮
4. 等待几秒，完成

### 操作 4：定期检查（1-2 周后）

**目的**：看看 Google 是否已经更新了你的网站

**怎么做**：

1. 在 Google Search Console 左侧菜单点击 **"网页"** 或 **"Pages"**
2. 查看索引的页面数量
3. 确认没有错误提示

**期望结果**：

- ✅ 旧的 HTTP 版本页面逐渐消失
- ✅ 新的 HTTPS www 版本页面增加
- ✅ 没有 "重复内容" 警告

---

**💡 小贴士**：Google 重新索引需要时间，通常 1-2 周才能看到明显变化，不用着急。

---

## 配置检查清单

完成配置后，使用此清单验证：

### Cloudflare 配置

- [ ] 检查 Dokploy 域名协议配置（HTTPS 或 HTTP）
- [ ] SSL/TLS 模式设置为 "Full"（如果 Dokploy 是 HTTPS）或 "Flexible"（如果 Dokploy 是 HTTP）
- [ ] "Always Use HTTPS" 已启用
- [ ] 重定向规则已创建（非 www → www，使用 Wildcard pattern 和 `${1}` 占位符）
- [ ] DNS 记录已设置为 Proxied（橙色云朵）
- [ ] HSTS 已启用（可选，建议最后启用）

### Dokploy 配置

- [ ] 域名配置为 HTTPS, Port: 3000（推荐）或 HTTP, Port: 3000
- [ ] 两个主域名都已配置（yourdomain.wiki 和 www.yourdomain.wiki）
- [ ] 不必要的 traefik.me 域名已删除（可选）

### 重定向测试

- [ ] `http://www.lucidblocks.wiki` → `https://www.lucidblocks.wiki` ✅
- [ ] `http://lucidblocks.wiki` → `https://www.lucidblocks.wiki` ✅
- [ ] `https://lucidblocks.wiki` → `https://www.lucidblocks.wiki` ✅
- [ ] `https://www.lucidblocks.wiki` 返回 200 OK ✅

### SSL 验证

- [ ] SSL 证书有效且受信任（Cloudflare 证书）
- [ ] 浏览器显示安全锁图标

### Google Search Console

- [ ] 首选域名已设置
- [ ] Sitemap 已更新为使用 HTTPS www 版本
- [ ] 重要页面已请求重新索引
- [ ] 所有多语言页面都正确重定向

---

## 预期效果

### SEO 改进

- ✅ 所有流量统一到 `https://www.lucidblocks.wiki`
- ✅ 消除重复内容问题
- ✅ 集中页面权重和排名
- ✅ 提升搜索引擎信任度

### 技术指标

- ✅ 所有 HTTP 请求自动重定向到 HTTPS
- ✅ 所有非 www 请求重定向到 www
- ✅ SSL/TLS 加密（客户端到 Cloudflare）
- ✅ 符合现代 Web 安全标准
- ✅ Dokploy 无需配置 SSL 证书，简化管理

### 用户体验

- ✅ 用户始终访问安全的 HTTPS 版本
- ✅ 浏览器显示安全锁图标
- ✅ 无论用户输入什么 URL，都会到达正确的地址
- ✅ 更快的加载速度（通过 Cloudflare CDN）

---

## 注意事项

### 1. 配置顺序很重要

按以下顺序配置：

1. ✅ 先检查 Dokploy 域名协议配置（HTTPS 或 HTTP）
2. ✅ 根据 Dokploy 配置选择 SSL/TLS 模式（Full 或 Flexible）
3. ✅ 再启用 Always Use HTTPS
4. ✅ 然后配置 www 重定向规则（使用 Wildcard pattern 和 `${1}` 占位符）
5. ⚠️ HSTS 应该最后启用（可选）

### 2. Flexible vs Full 模式

**推荐使用 Full 模式**：

- ✅ Dokploy 域名配置为 HTTPS（Traefik 自动生成证书）
- ✅ Cloudflare 使用 Full 模式
- ✅ 端到端加密，更安全
- ✅ 避免重定向循环问题

**备选 Flexible 模式**：

- ⚠️ 仅当 Dokploy 域名配置为 HTTP 时使用
- ⚠️ Cloudflare 到源服务器之间是 HTTP
- ⚠️ 如果源服务器有 HTTPS 重定向，会导致循环

### 3. DNS 传播时间

- ⏱️ DNS 更改可能需要 5-10 分钟生效
- ⚡ Cloudflare 规则通常立即生效
- 🌍 完全传播可能需要 24-48 小时

### 4. 缓存清理

配置完成后，在 Cloudflare 中清除缓存：

- **路径**: `Caching → Configuration → Purge Everything`

### 5. 监控和验证

- ✅ 配置后立即测试所有 URL 变体
- ✅ 监控 Google Search Console 的索引变化
- ✅ 检查是否有 404 错误或重定向循环

### 6. Dokploy 配置

**推荐配置**：

- ✅ Dokploy 域名配置为 HTTPS, Port: 3000
- ✅ Cert 保持 none（Traefik 自动生成证书）
- ✅ Cloudflare 使用 Full SSL 模式
- ✅ 确保 Dokploy 应用监听在 3000 端口

**备选配置**：

- ⚠️ Dokploy 域名配置为 HTTP, Port: 3000
- ⚠️ Cloudflare 使用 Flexible SSL 模式
- ⚠️ 注意可能的重定向循环问题

---

## 时间估计

| 任务                       | 预计时间          |
| -------------------------- | ----------------- |
| Cloudflare 配置            | 10-15 分钟        |
| Dokploy 检查（无需修改）   | 2 分钟            |
| DNS 传播                   | 5-10 分钟         |
| 测试验证                   | 10 分钟           |
| Google Search Console 更新 | 5 分钟            |
| **总计**                   | **约 30-40 分钟** |

⏰ **Google 重新索引**：配置生效后，Google 重新索引可能需要 1-2 周时间。

---

## 架构说明

### 流量路径

**推荐架构（Full SSL 模式）**：

```
用户浏览器
    ↓ HTTPS (SSL by Cloudflare)
Cloudflare CDN
    ↓ HTTPS (SSL by Traefik)
Dokploy (Port 3000, Protocol: HTTPS)
    ↓
Next.js 应用
```

**备选架构（Flexible SSL 模式）**：

```
用户浏览器
    ↓ HTTPS (SSL by Cloudflare)
Cloudflare CDN
    ↓ HTTP (内网连接)
Dokploy (Port 3000, Protocol: HTTP)
    ↓
Next.js 应用
```

### 架构优势

1. ✅ **简化证书管理**：Cloudflare 处理所有 SSL/TLS，无需在 Dokploy 配置证书
2. ✅ **全球加速**：利用 Cloudflare 的全球 CDN 加速
3. ✅ **自动防护**：自动 DDoS 防护和 WAF
4. ✅ **降低负载**：减轻源服务器负担
5. ✅ **统一管理**：所有域名的 SSL 在一个地方管理

### 安全层级

| 层级 | 组件       | 功能                         |
| ---- | ---------- | ---------------------------- |
| 1    | Cloudflare | SSL/TLS 终止、DDoS 防护、WAF |
| 2    | Cloudflare | 重定向规则、缓存、CDN        |
| 3    | Dokploy    | 容器编排、应用部署           |
| 4    | Next.js    | 应用逻辑、页面渲染           |

---

## 故障排查

### 问题 1：重定向循环（ERR_TOO_MANY_REDIRECTS）

**症状**：浏览器显示 "ERR_TOO_MANY_REDIRECTS"

**常见原因和解决方案**：

#### 原因 A：SSL 模式与 Dokploy 配置不匹配 ⭐ 最常见

**诊断**：

1. 检查 Dokploy Domains 中的 Protocol 字段
2. 检查 Cloudflare SSL/TLS 模式

**解决方案**：

| Dokploy Protocol | Cloudflare SSL 模式 | 结果          |
| ---------------- | ------------------- | ------------- |
| HTTPS            | Full                | ✅ 正确       |
| HTTPS            | Flexible            | ❌ 重定向循环 |
| HTTP             | Flexible            | ✅ 正确       |
| HTTP             | Full                | ❌ SSL 错误   |

**修复步骤**：

1. 进入 `Cloudflare Dashboard → SSL/TLS → Overview`
2. 如果 Dokploy 是 HTTPS，改为 `Full` 模式
3. 如果 Dokploy 是 HTTP，改为 `Flexible` 模式
4. 清除 Cloudflare 缓存（`Caching → Configuration → Purge Everything`）
5. 等待 2-3 分钟后测试

#### 原因 B：重定向规则配置错误

**诊断**：

- Request URL 包含了 www（会匹配所有请求，包括 www 域名）

**解决方案**：

1. 进入 `Cloudflare Dashboard → Rules → Redirect Rules`
2. 检查 Request URL 是否为 `https://yourdomain.wiki/*`（不带 www）
3. 如果包含 www，删除规则重新创建

#### 原因 C：浏览器缓存

**解决方案**：

1. 清除浏览器缓存
2. 使用无痕模式测试
3. 使用 `curl -I` 命令测试（不受浏览器缓存影响）

### 问题 2：SSL 证书错误

**症状**：浏览器显示 "Your connection is not private"

**解决方案**：

1. 等待 5-10 分钟让 Cloudflare 证书生效
2. 检查 DNS 记录是否为 Proxied（橙色云朵）
3. 验证域名是否正确添加到 Cloudflare

### 问题 3：非 www 不重定向

**症状**：`https://lucidblocks.wiki` 不重定向到 `https://www.lucidblocks.wiki`

**解决方案**：

1. 检查 Cloudflare 重定向规则是否已创建
2. 确认规则状态为 "Active"
3. 验证 DNS 记录 `@` 是否为 Proxied

### 问题 4：HTTP 仍然可以访问

**症状**：`http://www.lucidblocks.wiki` 不重定向到 HTTPS

**解决方案**：

1. 检查 "Always Use HTTPS" 是否已启用
2. 清除 Cloudflare 缓存
3. 等待 5-10 分钟让配置生效

---

## 相关资源

### Cloudflare 文档

- [SSL/TLS 加密模式](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/)
- [重定向规则](https://developers.cloudflare.com/rules/url-forwarding/)
- [HSTS 配置](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/)

### 工具

- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)
- [Redirect Checker](https://www.redirect-checker.org/)
- [HTTP Status Checker](https://httpstatus.io/)

### Google Search Console

- [设置首选域名](https://support.google.com/webmasters/answer/9008080)
- [提交 Sitemap](https://support.google.com/webmasters/answer/183668)
- [请求索引](https://support.google.com/webmasters/answer/6065812)

---

## 更新日志

| 日期       | 版本 | 更新内容                                                                                     |
| ---------- | ---- | -------------------------------------------------------------------------------------------- |
| 2026-02-09 | 1.0  | 初始版本 - 完整的 Cloudflare + Dokploy HTTPS 配置指南                                        |
| 2026-03-02 | 2.0  | 重大更新 - 修正 SSL 模式选择逻辑，添加 Wildcard pattern 重定向规则详细说明，增强故障排查部分 |

---

## 联系支持

如果遇到问题，可以：

1. 查看 [故障排查](#故障排查) 部分
2. 检查 Cloudflare 状态页面
3. 查看 Dokploy 日志
4. 联系 Cloudflare 支持（如果是 Cloudflare 相关问题）

---

**文档维护者**: Claude Code
**最后更新**: 2026-02-09
**适用版本**: Cloudflare (所有版本), Dokploy (所有版本)

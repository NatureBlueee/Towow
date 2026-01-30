# ToWow 网站大陆访问 CDN 配置指南

## 部署状态

**Vercel 部署成功**

| 项目 | 值 |
|------|-----|
| 项目名称 | towow-website |
| 生产环境 URL | https://towow-website.vercel.app |
| 部署时间 | 2026-01-30 |
| 框架 | Next.js 16.1.6 |
| 构建状态 | 成功 (静态生成) |

---

## 中国大陆访问现状分析

### Vercel 在中国的访问情况

1. **vercel.app 域名**: 在中国大陆访问速度较慢，部分地区可能不稳定
2. **原因**: Vercel 的边缘节点主要分布在海外，中国大陆没有节点
3. **延迟**: 从中国访问通常有 200-500ms 的延迟

### 核心问题

| 问题 | 说明 |
|------|------|
| 无中国节点 | Vercel Edge Network 在中国大陆没有 PoP 点 |
| 跨境延迟 | 请求需要跨越国际出口，延迟高 |
| 稳定性 | 高峰期可能出现丢包或超时 |

---

## 解决方案对比

### 方案 1: Cloudflare CDN (推荐 - 无需备案)

**适用场景**: 面向海外用户为主，兼顾中国用户基本访问

**优点**:
- 免费计划可用
- 配置简单
- 无需 ICP 备案
- 提供 DDoS 防护和 SSL

**缺点**:
- 中国大陆访问速度提升有限（Cloudflare 在中国也没有节点）
- 部分 Cloudflare IP 在中国可能被干扰

**配置步骤**:

1. 在 Cloudflare 注册并添加你的域名
2. 在 Vercel 添加自定义域名
3. 在 Cloudflare DNS 配置:

```
# A 记录 (Proxy 关闭)
Type: A
Name: @
Value: 76.76.21.21  # 从 Vercel 域名设置获取
Proxy: OFF (DNS only)

# CNAME 记录 (Proxy 关闭)
Type: CNAME
Name: www
Value: cname.vercel-dns.com
Proxy: OFF (DNS only)
```

4. SSL/TLS 设置为 "Full" 或 "Full (Strict)"

**注意**: Proxy 必须关闭，否则会与 Vercel 的 SSL 冲突

---

### 方案 2: 阿里云/腾讯云 CDN (需要备案)

**适用场景**: 主要面向中国大陆用户

**优点**:
- 中国大陆节点覆盖广
- 访问速度快（延迟 < 50ms）
- 稳定性好

**缺点**:
- 需要 ICP 备案（1-2 个月）
- 需要中国大陆服务器或使用回源
- 有一定成本

**ICP 备案要求**:

| 类型 | 说明 | 时间 | 适用对象 |
|------|------|------|----------|
| ICP 备案 (Bei'An) | 非商业网站 | 1-2 个月 | 个人/企业 |
| ICP 许可证 (ICP Zheng) | 商业网站 | 2-3 个月 | 仅限中国企业 |

**备案流程**:
1. 准备材料（身份证/营业执照、域名证书等）
2. 通过云服务商提交备案申请
3. 管局审核（约 20 个工作日）
4. 获得备案号，在网站底部展示

---

### 方案 3: Cloudflare China Network (企业级)

**适用场景**: 大型企业，有预算和合规需求

**优点**:
- 通过京东云合作在中国有节点
- 性能提升 60%+
- 合规

**缺点**:
- 仅限企业版客户
- 价格较高
- 仍需 ICP 备案

---

### 方案 4: 香港服务器中转 (折中方案)

**适用场景**: 不想备案，但需要改善中国访问

**架构**:
```
中国用户 -> 香港 CDN/服务器 -> Vercel
```

**可选服务**:
- 阿里云香港 CDN
- 腾讯云香港 CDN
- AWS CloudFront (香港节点)

**优点**:
- 无需备案
- 比直连 Vercel 快
- 延迟约 50-100ms

**缺点**:
- 有一定成本
- 配置较复杂

---

## 推荐方案

### 短期方案 (立即可用)

**使用 Cloudflare + 自定义域名**

1. 购买一个域名（如 towow.com）
2. 在 Cloudflare 管理 DNS
3. 在 Vercel 绑定自定义域名
4. Cloudflare Proxy 设为 OFF

这样可以:
- 使用自定义域名而非 vercel.app
- 获得 Cloudflare 的 SSL 和基础防护
- 中国用户可以正常访问（速度一般）

### 长期方案 (如果中国用户是主要目标)

**ICP 备案 + 国内 CDN**

1. 注册域名并完成 ICP 备案
2. 使用阿里云/腾讯云 CDN
3. 配置回源到 Vercel 或部署到国内服务器

---

## 配置检查清单

- [ ] 自定义域名已购买
- [ ] DNS 已配置到 Cloudflare
- [ ] Vercel 已添加自定义域名
- [ ] SSL 证书已生效
- [ ] 中国大陆访问测试通过

---

## 测试工具

| 工具 | 用途 | 链接 |
|------|------|------|
| 拨测 | 中国各地访问测试 | https://www.boce.com |
| 17CE | 全国节点测速 | https://www.17ce.com |
| Ping.pe | 全球 Ping 测试 | https://ping.pe |

---

## 参考资料

- [Cloudflare + Vercel 配置指南](https://gist.github.com/nivethan-me/a56f18b3ffbad04bf5f35085972ceb4d)
- [Cloudflare ICP 说明](https://developers.cloudflare.com/china-network/concepts/icp/)
- [Cloudflare China Express](https://blog.cloudflare.com/china-express)
- [Vercel 官方文档](https://vercel.com/docs/getting-started-with-vercel)

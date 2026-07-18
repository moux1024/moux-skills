# Tencent Official Documentation Map

Use this map when Mini Program behavior, configuration, capabilities, review rules, or platform limits matter. Prefer Tencent official docs over third-party tutorials. If an online tutorial conflicts with the official docs, follow the official docs and mention the conflict as a risk or assumption.

Primary entry:

- WeChat Mini Program framework: https://developers.weixin.qq.com/miniprogram/dev/framework/

## Core Framework

| Task | Official page | Use for |
|---|---|---|
| Project and page file layout | https://developers.weixin.qq.com/miniprogram/dev/framework/structure.html | Required root files, page file groups, uploadable file types |
| Global and page configuration | https://developers.weixin.qq.com/miniprogram/dev/framework/config.html | `app.json`, page `.json`, window behavior, tabBar, network timeout, config override rules |
| Register the app | https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/app.html | `App()`, app lifecycle, global data, app-level startup logic |
| Register pages | https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/page.html | `Page()`, page data, lifecycle callbacks, event handlers, `setData` usage |
| Page lifecycle | https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/page-life-cycle.html | Page load/show/hide/unload timing and side effects |
| Routing | https://developers.weixin.qq.com/miniprogram/dev/framework/app-service/route.html | Navigation methods, route stack behavior, tab page limits |

## View Layer

| Task | Official page | Use for |
|---|---|---|
| WXML | https://developers.weixin.qq.com/miniprogram/dev/framework/view/wxml/ | Page structure, data binding, list rendering, conditional rendering, templates, imports |
| WXSS | https://developers.weixin.qq.com/miniprogram/dev/framework/view/wxss.html | Style rules, responsive units, selectors, global/page styles |
| Events | https://developers.weixin.qq.com/miniprogram/dev/framework/view/wxml/event.html | Event binding, bubbling/capturing, dataset, event detail |
| WXS | https://developers.weixin.qq.com/miniprogram/dev/framework/view/wxs/ | View-layer scripting and supported runtime differences |

## Components And APIs

| Task | Official page | Use for |
|---|---|---|
| Built-in components | https://developers.weixin.qq.com/miniprogram/dev/component/ | Choosing native UI components before custom code |
| Component framework | https://developers.weixin.qq.com/miniprogram/dev/framework/custom-component/ | Custom components, properties, observers, lifetimes, communication |
| API index | https://developers.weixin.qq.com/miniprogram/dev/api/ | `wx.*` API availability, parameters, callbacks, Promises, permissions |
| Login | https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html | `wx.login`, auth code flow, backend exchange requirements |
| User information | https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/userProfile.html | User profile collection flow and consent requirements |
| Share | https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/share.html | Share handlers, page share behavior, share tickets |
| Subscribe messages | https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/subscribe-message.html | User opt-in, template messages, send timing |

## Cloud, Security, And Compliance

| Task | Official page | Use for |
|---|---|---|
| Cloud Development | https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloud/basis/getting-started.html | Cloud environment, cloud functions, database, storage |
| Content security | https://developers.weixin.qq.com/miniprogram/dev/framework/security.imgSecCheck.html | Text/image/content moderation capabilities and limits |
| Privacy protection | https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/ | Privacy interface, privacy authorization, personal information handling |
| Security guidelines | https://developers.weixin.qq.com/miniprogram/dev/framework/security.html | Platform security expectations and sensitive operation handling |

## Tools, Performance, And Release

| Task | Official page | Use for |
|---|---|---|
| Developer Tools | https://developers.weixin.qq.com/miniprogram/dev/devtools/devtools.html | Local preview, debugging, upload, project settings |
| npm support | https://developers.weixin.qq.com/miniprogram/dev/devtools/npm.html | Installing and building npm packages for Mini Programs |
| Performance | https://developers.weixin.qq.com/miniprogram/dev/framework/performance/ | Startup, rendering, package size, runtime performance |
| Reasonable `setData` usage | https://developers.weixin.qq.com/miniprogram/dev/framework/performance/tips/runtime_setData.html | Avoiding large/frequent updates and render overhead |
| Subpackages | https://developers.weixin.qq.com/miniprogram/dev/framework/subpackages.html | Package splitting, load timing, independent packages |
| Collaboration and release | https://developers.weixin.qq.com/miniprogram/dev/framework/quickstart/release.html | Upload, test version, review, and release flow |

## Usage Rules

- Record the official page consulted in `docs/ai/miniapp/current-plan.md` when it affects a decision.
- For native Mini Program code, use official framework, component, and API pages first; use framework-specific docs only when the project uses Taro, uni-app, or another abstraction.
- Do not copy large official examples into project docs. Summarize the relevant rule and link the official page.
- For privacy, payment, login, phone number, location, UGC, upload, review, or release tasks, treat official docs as required reading before implementation.
- If a Tencent page has moved, search only within `developers.weixin.qq.com` first and update this map when the new official URL is confirmed.

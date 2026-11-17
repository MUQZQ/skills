# 已验证的接口录入流程

基址：`https://qedai.df2cloud.com:60008/serve/patodo/outer-ai-usage/api`。
以下来自 2026-11-13 网站实际前端调用和成功操作。接口变化时先检查当前应用公开前端资源或页面网络请求，确认后再修改参数；不要猜接口或切换开发模式。

## 会话与调用

使用已登录目标页面的同源 fetch，浏览器自然携带当前会话。本次通过 cua_repl 的 `tab.capabilities.get("cdp")`，读取其 documentation 后，使用 `Runtime.evaluate` 执行 fetch，设置 `awaitPromise: true, returnByValue: true`。遵守当前工具实际支持范围；不要用仅允许 DOM 只读的 evaluate 接口发送请求。若当前环境不允许此方式，改用已授权的连接器或页面操作，不规避工具限制。

JSON 请求为 POST，`Content-Type: application/json`。查询和普通 mutation 使用 `{params: {...}}`；事务使用 `{mutations: [...]}`。检查 HTTP 为 2xx 且响应 `success === true`，读取 `data`。不要仅凭请求没有抛错认定成功。

## 查重和选项

| 路径 | 请求内容 |
| --- | --- |
| `/queries/subscription_purposes.list` | `{params:{limit:200,offset:0}}`，读取用途名称和 ID，不能硬编码 ID |
| `/queries/ai_subscriptions.forReimbursementPerson` | `{params:{userName,limit:500,offset:0}}`，包含历史提交和转账记录 |
| `/queries/ai_subscriptions.get` | `{params:{id}}` |
| `/queries/subscription_attachments.forSubscription` | `{params:{subscriptionId:id,limit:200,offset:0}}` |

读取 `data.rows`；满页时增加 offset 继续查询，直到最后一页。查重不仅比较项目名称：同一发票可能被错误命名为另一个套餐。匹配使用人、日期、原始币种和金额、人民币实付，再比较已有附件文件名中的发票号；必要时核对附件内容。已存在则跳过并报告 ID。汇总费用若可能包含历史已报费用，先核对组成，不能仅凭总额不同就断定没有重复。

## 上传附件

`POST /content/upload`，使用 FormData 的 `file` 字段，保留原文件名和正确 MIME（PDF、PNG、JPEG）。本次可在 cua_repl 中读取用户已授权的本地文件，以 base64 携带到同源执行环境，构造 Uint8Array → File → FormData；不要将文件内容、base64 或会话信息打印出来。不要手写 multipart 的 Content-Type，交给 fetch 生成 boundary。

成功响应可能是 **HTTP 201**：`{success:true,data:{key,url}}`。保存每份返回值与原文件名、分类的对应关系。三类值为 `invoice`、`payment_proof`、`expiry_proof`。发票及配套收据可放在 invoice；人民币代购转账和手续费说明放 payment_proof；对应订阅期间的账单截图放 expiry_proof。用户明确指定的无到期 API 用量截图也可放 expiry_proof。

## 一笔费用及附件一起保存

`POST /mutations/_transaction`：

```json
{
  "mutations": [
    {"name":"$ai_subscriptions.create","params":"此处替换为下述费用参数对象"},
    {"name":"$subscription_attachments.create","params":{
      "subscriptionId":{"$result":0,"field":"lastInsertRowId"},
      "attachmentType":"invoice",
      "fileName":"实际文件名.pdf",
      "fileUrl":"上传返回的 url",
      "fileKey":"上传返回的 key",
      "mimeType":"application/pdf"
    }}
  ]
}
```

每份附件增加一个 create 项。费用参数：

| 参数 | 值与要求 |
| --- | --- |
| accountId | 已确认的关联账号 ID 或 null |
| purposeId | 根据本次用户指定用途从选项接口取 ID，必填 |
| userName / invoiceLocation | 本次指定使用人 / 发票归属地 |
| orderedAt | 有依据的本地日期时间 `YYYY-MM-DDTHH:mm`，未知则空字符串 |
| startsAt | `YYYY-MM-DD`；无单一开始日期的汇总一次性费用可为空字符串 |
| vendor / subscriptionItem | 供应商及真实项目名称 |
| isForeign | 1 或 0 |
| resellerVendor | 代购名称及已知手续费说明，或 null |
| billingCycle | 已验证 `monthly`、`one_time`；其他周期先读取当前前端映射 |
| customCycleValue / customCycleUnit | 非自定义周期均为 null |
| originalAmountMinor / originalCurrency | 原币金额的最小单位整数与币种；CNY、USD 按分，不能对所有币种一律乘 100 |
| paidAmountMinor / paidCurrency | 真实人民币实付的分整数 / `CNY`，含有凭证支持的代购手续费 |
| expiresOn | 月付按真实期间填写 `YYYY-MM-DD`；一次性无到期费用为 null |

金额转换用十进制精确转换或校验过的整数，不让浮点误差产生小数分。升级账单使用抵扣后含税应付原币金额，不把套餐标价当实际金额。

事务 `data` 为结果数组，各项应有 `changes:1`；第一项 `lastInsertRowId` 是费用 ID，其余为附件关联 ID。上传文件本身早于事务，不受该事务回滚保护。保存超时或响应不明时，先重新查询人员费用和附件判断是否成功，不能重跑整个批次；逐笔保存、逐笔记下已成功 ID。

## 保存后核对

1. 根据实际返回的费用 ID 查询详情，不能猜连续 ID。
2. 核对 `user_name`、`invoice_location`、`purpose_name`、`vendor`、`subscription_item`、`starts_at`、`expires_on`、`billing_cycle`、原币和人民币金额、代购说明。
3. 查询该笔附件，比较预期与实际的文件名、`attachment_type`、key/url 和 MIME；检查发票、付款、有效期三类计数。不能把上传成功等同于附件已关联到记录。
4. 读取 `is_approved`、`reimbursement_status`；新建后本次观察为 `0` 和 `not_submitted`。如实报告待审批，不能自行推进审批或转账。
5. 刷新页面，用新 ID 核对可见列表并保存截图。若曾打开未保存表单，关闭并放弃该旧草稿，避免稍后再次保存造成重复。
6. 给用户表格：ID、费用、人民币金额、附件数量和真实状态，并说明跳过的重复项。

页面备用流程只在接口不可用时采用。文件 input 可能是 `sr-only`，应点击对应可见 label 触发文件选择器；不要反复强制点击隐藏 input。日期控件需在操作后核对实际值，本次普通 fill 曾未改变日期，而 cua `setValue` 有效。

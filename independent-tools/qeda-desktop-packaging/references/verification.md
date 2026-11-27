# 安装包交付核验清单

在打包工作树根目录执行（把 `P` 指向工作树，`SETUP` 指向安装包）。

```bash
P=E:/worktrees/QEDAgent/QEDAgent_user-guide-pilot
# 构建号每次 +1；用本次 bump 脚本输出的版本，下例为 2.2609.2.1
SETUP="$P/release/package-profile/QEDAgent-Setup-2.2609.2.1.HND-x64.exe"
APP="$P/release/package-profile/win-unpacked"
```

## 1. 安装包本身

```bash
node -e "const fs=require('fs'),c=require('crypto');const b=fs.readFileSync(process.argv[1]);console.log('size:',b.length);console.log('sha256:',c.createHash('sha256').update(b).digest('hex'))" "$SETUP"
powershell.exe -NoProfile -Command "(Get-AuthenticodeSignature '$SETUP').Status"
```

预期：本机无证书时 `NotSigned`；有签名时 `Valid` 且签名者与发布主体一致。

## 2. 目录包内容（真机验收对象）

```bash
node -e "
const {listPackage,extractFile}=require('@electron/asar');const fs=require('fs'),c=require('crypto');
const app=process.argv[1];const asar=app+'/resources/app.asar';
const files=listPackage(asar).map(p=>p.split(String.fromCharCode(92)).join('/').replace(/^\/+/,''));
const read=p=>extractFile(asar,p.split('/').join(String.fromCharCode(92)));
for (const f of ['resources/sch-extension/dist/extension-config.js','resources/pcb-qml/copilot/CopilotPanel.qml','resources/sds-websocket-client/dist/manifest.json']) {
  const hit=files.find(x=>x===f); if(!hit){console.log(f,'MISSING');continue}
  const t=read(hit).toString('utf8');
  console.log(f,'| 目标端口:',t.includes('38080'),'| 旧端口残留:',/(?<![0-9])8080(?![0-9])/.test(t));
}
console.log('模型:',files.filter(x=>/symbol.*\.onnx$/.test(x)).join(', ')||'none','| 旧模型:',files.filter(x=>x.includes('yolov8m_symbol')).length);
const g=JSON.parse(read('frontend/dist/help/guide.json').toString('utf8'));
console.log('帮助:',g.unavailable===true?'unavailable':'articles '+g.articles.length);
" "$APP"
```

同时确认 `$APP/resources/app.asar.unpacked/node_modules/onnxruntime-node/bin/napi-v6/win32/x64/onnxruntime_binding.node` 存在。

## 3. 安装包内 asar 与载荷

```bash
rm -rf /e/worktrees/QEDAgent/_verify && mkdir -p /e/worktrees/QEDAgent/_verify
"/c/Program Files/7-Zip/7z.exe" x "$SETUP" -o/e/worktrees/QEDAgent/_verify '$PLUGINSDIR\app-64.7z' '$PLUGINSDIR\cust-payload.zip' -y
"/c/Program Files/7-Zip/7z.exe" x "/e/worktrees/QEDAgent/_verify/$(printf '$PLUGINSDIR')/app-64.7z" -o/e/worktrees/QEDAgent/_verify/app 'resources\app.asar' -y
node -e "
const fs=require('fs'),c=require('crypto');const h=p=>c.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const a=h('E:/worktrees/QEDAgent/_verify/app/resources/app.asar');
const b=h('$APP/resources/app.asar');
console.log('installer asar == unpacked:',a===b?'MATCH':'MISMATCH');
const rel=JSON.parse(fs.readFileSync('$P/scripts/windows-cust-tools-release.json','utf8'));
const p=h('E:/worktrees/QEDAgent/_verify/'+String.fromCharCode(36)+'PLUGINSDIR/cust-payload.zip');
console.log('installer cust payload:',p===rel.sha256['payload.zip']?'MATCH '+rel.payloadVersion:'MISMATCH');
"
rm -rf /e/worktrees/QEDAgent/_verify
```

## 4. 版本号三层

```bash
node -e "console.log('package:',require('$P/package.json').version)"
grep -nE 'artifactName|buildVersion|uninstallDisplayName' "$P/electron-builder.yml"
powershell.exe -NoProfile -Command "(Get-Item '$APP/QEDAgent.exe').VersionInfo | Select-Object FileVersion,ProductVersion"
node -e "const m=require('$P/resources/sch-extension/dist/manifest.json');console.log('ext version:',m.version,'version_name:',m.version_name)"
```

预期：内部 semver 合法、文件名/显示名含完整交付标识、FileVersion 四段数字、
扩展 `version` 为数字且 `version_name` 为完整字符串。

## 5. 打包过程证据

- 真机验收：`Tests 1 passed`；
- VC++：`embedded Microsoft VC++ x64 <版本>`；
- 客户工具：`embedded customer tools <载荷版本>`；
- 帮助：`articles 53`（或与当前清单一致）。

## 6. 常见不一致

| 现象 | 先查 |
|---|---|
| 端口仍是 8080 | `.desktop-package` 是否为本次构建、SCH 资源是否重建 |
| 模型缺失/旧模型 | `runtimePackages` 是否含 `onnxruntime-node`，assets 是否替换 |
| 客户载荷 MISMATCH | 检查是否在构建中途重跑过 stage，重新按顺序执行第 4-5 步 |
| 版本号文件名不对 | `artifactName` 是否为更新后的字面量；是否用了旧安装包路径 |
| 包内扩展 zip 端口不对 | zip 是否用新 `resources/sch-extension/dist` 重新生成 |

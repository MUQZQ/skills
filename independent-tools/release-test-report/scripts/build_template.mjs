import fs from "node:fs/promises";
import path from "node:path";
import {SpreadsheetFile,Workbook} from "@oai/artifact-tool";
const caseHeaders = ["类型","小类","编号","需求","需求描述（含规格）","是否必选","需求满足程度",
 "当前版本已知覆盖","待补证及范围差异","功能责任人（原登记）","验收标准","主测人","测试方法（使用正式包）",
 "预期结果","测试结论","实际测试结果","备注／来源"];
const evidenceHeaders=["编号","证据类别","功能范围","场景来源／检查项","验证方式","预期行为",
  "记录的实际结果","结果","对应提交／状态","来源编号／轮次","检查证据","备注／截图"];
const coverageHeaders=["模块","发布功能","本版业务及裁剪边界","关联 PR","证据状态","首选 PR 佐证编号","分支归档编号","原图编号","冒烟用例","正式版状态","最近相关评审","证据缺口与适用范围","规格／责任田依据"];
const prHeaders=["编号","PR 主题","相关发布功能","纳入基线依据","合入提交","评审轮次","评审提交",
  "PR Helper 轮次结论","收录场景记录","已附截图","代码 PR","PR Helper","补证说明"];

const FONT="Microsoft YaHei", INK="#27374A", MUTED="#536579", GREY="#4C637F", HEADER="#264866", BLUE="#173652", LIGHT="#E9F1FA", BAND="#F4F7FB", RULE="#D7E2EC", AMBER="#FFF1D2", RED="#FCE6E4", GREEN="#E4F3E9", LINK="#21609B";
const col=(index)=>String.fromCharCode(65+index);
function onRange(sheet,address) {return sheet.getRange(address);}
function formatBody(sheet,address) {
  const block=onRange(sheet,address);
  block.format.font={name:FONT,size:10,color:INK};
  block.format.wrapText=true;
  block.format.verticalAlignment="center";
}
function header(sheet,address,color=HEADER) {
  const block=onRange(sheet,address);
  block.format.fill=color;
  block.format.font={name:FONT,size:10.5,bold:true,color:"#FFFFFF"};
  block.format.horizontalAlignment="center";
  block.format.verticalAlignment="center";
  block.format.wrapText=true;
  block.format.rowHeight=34;
}
function setWidths(sheet,widths) {
  widths.forEach((width,i)=>onRange(sheet,col(i)+":"+col(i)).format.columnWidthPx=width);
}
function heightFor(row,widths,min,max) {
  const lines=Math.max(...row.map((v,i)=>String(v??"").split("\n").reduce((n,t)=>{
    const px=Array.from(t).reduce((a,c)=>a+(c.charCodeAt(0)>255?13:7),0);
    return n+Math.max(1,Math.ceil(px/Math.max(widths[i]-15,26)));
  },0)));
  return Math.min(max,Math.max(min,lines*14+12));
}
function tuneTable(sheet,last,{key=[],center=[],numeric=[],groups=[],accent=[]}={}) {
  const columnRange=(column)=>onRange(sheet,column+"2:"+column+last);
  for (const column of [...center,...numeric]) columnRange(column).format.horizontalAlignment="center";
  for (const column of key) columnRange(column).format.font={name:FONT,size:10,color:BLUE,bold:true};
  for (const [address,color] of groups) onRange(sheet,address).format.fill=color;
  for (const [column,color] of accent) columnRange(column).format.fill=color;
}
function tableSheet(sheet,head,rows,widths,name,min,max,{frozen=0,tab=HEADER,module}={}) {
  sheet.showGridLines=false;
  sheet.tabColor=tab;
  const last=rows.length+1, endCol=col(head.length-1), address="A1:"+endCol+last;
  onRange(sheet,address).values=[head,...rows];
  const table=sheet.tables.add(address,true,name);
  table.style="TableStyleLight1";
  table.showBandedRows=false;
  table.showFilterButton=true;
  sheet.freezePanes.freezeRows(1);
  if(frozen)sheet.freezePanes.freezeColumns(frozen);
  setWidths(sheet,widths);
  formatBody(sheet,address);
  header(sheet,"A1:"+endCol+"1");
  rows.forEach((row,i)=>{
    const line=i+2, area=onRange(sheet,"A"+line+":"+endCol+line);
    area.format.fill=i%2?BAND:"#FFFFFF";
    area.format.rowHeight=heightFor(row,widths,min,max);
    if(module!==undefined && i>0 && row[module]!==rows[i-1][module]){
      area.format.borders={top:{style:"thin",color:RULE}};
    }
  });
  return last;
}
function flag(sheet,column,last,statuses) {
  for (const [status,fill,color] of statuses) onRange(sheet,column+"2:"+column+last).conditionalFormats.addCustom(
    "=$"+column+'2="'+status+'"',{fill,font:{bold:true,color:color??INK}},
  );
}
function flagPositive(sheet,address,column,row,fill,color=INK) {
  const ref="$"+column+row;
  onRange(sheet,address).conditionalFormats.addCustom("=AND(ISNUMBER("+ref+"),"+ref+">0)",{fill,font:{bold:true,color}});
}
function rowFill(sheet,line,last,color) {
  onRange(sheet,"A"+line+":"+last+line).format.fill=color;
}
function styleText(sheet,address,{size=10,bold=false,color=INK}={}) {
  onRange(sheet,address).format.font={name:FONT,size,bold,color};
}
function merge(sheet,address,value) {
  sheet.mergeCells(address);
  onRange(sheet,address.split(":")[0]).values=[[value]];
}
function link(sheet,address,url,label) {
  const target=onRange(sheet,address);
  const esc=(value)=>String(value).replace(/"/g,'""');
  target.formulas=[['=HYPERLINK("'+esc(url)+'","'+esc(label)+'")']];
  target.format.font={name:FONT,size:10,bold:true,color:LINK,underline:"single"};
}
function section(sheet,row,label,last="I") {
  merge(sheet,"A"+row+":"+last+row,label);
  header(sheet,"A"+row+":"+last+row,GREY);
  onRange(sheet,"A"+row).format.horizontalAlignment="left";
  onRange(sheet,"A"+row).format.rowHeight=28;
}


const target=process.argv[2];
if(!target)throw Error("缺少模板输出的目录。");
const workbook=Workbook.create();
const summary=workbook.worksheets.add("发布测试摘要");
const coverage=workbook.worksheets.add("发布功能覆盖");
const cases=workbook.worksheets.add("测试自测结论");
const prs=workbook.worksheets.add("PR 证据索引");
const evidence=workbook.worksheets.add("测试证据");
const shots=workbook.worksheets.add("证据截图");
const blanks=(rows,columns)=>Array.from({length:rows},()=>Array(columns).fill(null));

const coverageEnd=tableSheet(coverage,coverageHeaders,blanks(12,coverageHeaders.length),
  [148,182,303,165,161,226,112,193,168,138,156,340,250],"ReleaseFeatureCoverage",44,182,{frozen:2,tab:"#305879",module:0});
tuneTable(coverage,coverageEnd,{key:["A","B"],center:["E","G","J","K"],groups:[["D1:H1","#395973"],["I1:K1","#315F65"]]});
flag(coverage,"E",coverageEnd,[["已有部分历史 PR 佐证",LIGHT,"#2B557F"],["仅分支归档证据",AMBER,"#824F1D"],["缺少直接测试证据",RED,"#9B3835"]]);
const casesEnd=tableSheet(cases,caseHeaders,blanks(24,caseHeaders.length),
  [76,116,91,190,227,93,131,218,225,153,264,112,422,335,104,218,292],"ReleaseSmokeCases",74,210,{frozen:4,tab:"#327177",module:1});
tuneTable(cases,casesEnd,{key:["C","D","L"],center:["A","B","C","F","G","L","O"],
  groups:[["D1:K1","#395973"],["L1:N1","#315F65"],["O1:P1","#735125"]],accent:[["L","#EAF2F9"],["P","#FFF8E8"]]});
const lastValidationRow=1000;
onRange(cases,"O2:O"+lastValidationRow).dataValidation={rule:{type:"list",values:["待执行","通过","失败","受阻","不适用"]}};
flag(cases,"O",lastValidationRow,[["待执行",AMBER,"#824F1D"],["通过",GREEN,"#2E624B"],["失败",RED,"#9B3835"],["受阻",RED,"#9B3835"],["不适用",BAND,MUTED]]);
const prEnd=tableSheet(prs,prHeaders,blanks(12,prHeaders.length),
  [78,255,233,155,250,96,250,222,122,104,120,158,255],"ReleasePrIndex",42,150,{frozen:2,tab:"#5C6E83"});
tuneTable(prs,prEnd,{key:["A","B"],center:["A","F","I","J","K","L"],groups:[["F1:J1","#395973"],["K1:L1","#315F65"]]});
const evEnd=tableSheet(evidence,evidenceHeaders,blanks(16,evidenceHeaders.length),
  [65,119,168,304,145,296,400,90,241,158,295,255],"ReleaseTestEvidence",44,239,{frozen:1,tab:"#5C6E83"});
tuneTable(evidence,evEnd,{key:["A","D","J"],center:["A","B","H","J"],groups:[["D1:H1","#395973"],["I1:L1","#315F65"]]});
flag(evidence,"H",evEnd,[["通过",GREEN,"#2E624B"],["失败",RED,"#9B3835"],["范围差异",RED,"#9B3835"],
  ["受阻",AMBER,"#824F1D"],["未完成",AMBER,"#824F1D"],["待确认",AMBER,"#824F1D"]]);

shots.showGridLines=false;
shots.tabColor=MUTED;
setWidths(shots,[110,106,106,106,106,106,22,110,106,106,106,106,106]);
formatBody(shots,"A1:M26");
merge(shots,"A1:M1","PR Helper 测试截图");
styleText(shots,"A1",{size:19,bold:true,color:BLUE});
onRange(shots,"A1").format.rowHeight=36;
merge(shots,"A2:M2","图号与评审轮次对应。填入来源、提交和证据编号，附所对应的原图与链接。");
styleText(shots,"A2",{color:MUTED});
onRange(shots,"A2").format.rowHeight=27;
onRange(shots,"A3").format.rowHeight=9;
shots.freezePanes.freezeRows(2);
for(const [from,to] of [["A","F"],["H","M"]]){
  onRange(shots,from+"4:"+to+"25").format.fill=BAND;
  onRange(shots,from+"4:"+to+"25").format.borders={bottom:{style:"thin",color:RULE}};
  merge(shots,from+"4:"+to+"4","图号　PR／轮次　场景");
  header(shots,from+"4:"+to+"4",GREY);
  onRange(shots,from+"4").format.horizontalAlignment="left";
  merge(shots,from+"5:"+to+"5","评审日期　提交　证据编号　关联功能");
  onRange(shots,from+"5").format.rowHeight=31;
  styleText(shots,from+"5",{color:MUTED});
  merge(shots,from+"6:"+to+"6","原图链接");
  styleText(shots,from+"6",{color:LINK,bold:true});
  onRange(shots,from+"6").format.rowHeight=20;
  for(let row=7;row<=25;row++)onRange(shots,from+row).format.rowHeight=16;
  onRange(shots,from+"26").format.rowHeight=11;
}

summary.showGridLines=false;
summary.tabColor=BLUE;
setWidths(summary,[156,121,83,82,108,85,128,129,214]);
formatBody(summary,"A1:I43");
function info(line,label,value,height=28){
  onRange(summary,"A"+line).values=[[label]];
  styleText(summary,"A"+line,{bold:true,color:BLUE});
  merge(summary,"B"+line+":I"+line,value);
  if(line%2===0)rowFill(summary,line,"I",BAND);
  onRange(summary,"A"+line).format.rowHeight=height;
}
merge(summary,"A2:I2","发布测试阶段报告");
styleText(summary,"A2",{size:23,bold:true,color:BLUE});
onRange(summary,"A1").format.rowHeight=12;
onRange(summary,"A2").format.rowHeight=44;
onRange(summary,"A2:I2").format.borders={bottom:{style:"thin",color:RULE}};
info(3,"汇报结论","",42);
rowFill(summary,3,"I",AMBER);
styleText(summary,"A3",{size:11,bold:true,color:"#764611"});
styleText(summary,"B3",{size:12,bold:true,color:"#623E19"});
info(4,"发布版本","");
info(5,"历史证据基线","");
info(6,"发布范围","");
info(7,"当前正式安装包","",38);
info(8,"证据范围","",32);
info(9,"PR 缺口与冒烟","",34);
onRange(summary,"A10").format.rowHeight=11;
section(summary,11,"按发布模块核对证据");
onRange(summary,"A12:I12").values=[["发布模块","清单功能数","历史 PR 佐证","仅归档","缺直接证据","用例数","验证入口","分工","对应明细"]];
header(summary,"A12:I12");
const featureModules="ReleaseFeatureCoverage[模块]";
const proofStatuses="ReleaseFeatureCoverage[证据状态]";
const smokeModules="ReleaseSmokeCases[小类]";
const caseId="ReleaseSmokeCases[编号]";
const caseState="ReleaseSmokeCases[测试结论]";
const actual="ReleaseSmokeCases[实际测试结果]";
const modeCols=[["C","已有部分历史 PR 佐证"],["D","仅分支归档证据"],["E","缺少直接测试证据"]];
for(let line=13;line<=19;line++){
  rowFill(summary,line,"I",line%2===0?BAND:"#FFFFFF");
  styleText(summary,"A"+line,{bold:true,color:BLUE});
  onRange(summary,"A"+line).format.rowHeight=27;
  const cell="$A"+line;
  const ifModule=(formula)=>'=IF('+cell+'="","",'+formula+')';
  onRange(summary,"B"+line).formulas=[[ifModule("COUNTIF("+featureModules+","+cell+")")]];
  for(const [column,status] of modeCols){
    onRange(summary,column+line).formulas=[[ifModule('COUNTIFS('+featureModules+','+cell+','+proofStatuses+',"'+status+'")')]];
  }
  onRange(summary,"F"+line).formulas=[[ifModule("COUNTIF("+smokeModules+","+cell+")")]];
  onRange(summary,"G"+line).formulas=[[ifModule('"见冒烟结果"')]];
  onRange(summary,"I"+line).formulas=[[ifModule('"发布功能覆盖"')]];
}
onRange(summary,"A20").values=[["功能项合计"]];
onRange(summary,"B20").formulas=[["=COUNTA(ReleaseFeatureCoverage[发布功能])"]];
for(const [column,status] of modeCols)onRange(summary,column+"20").formulas=[['=COUNTIF('+proofStatuses+',"'+status+'")']];
onRange(summary,"G20").values=[["见冒烟结果"]];
onRange(summary,"I20").values=[["通用冒烟用例可单列。"]];
rowFill(summary,20,"I",LIGHT);
onRange(summary,"A20").format.rowHeight=33;
styleText(summary,"A20:I20",{size:11,bold:true,color:BLUE});
onRange(summary,"B13:H20").format.horizontalAlignment="center";
styleText(summary,"G13:G20",{bold:true,color:"#795324"});
flagPositive(summary,"D13:D20","D",13,AMBER,"#854F1D");
flagPositive(summary,"E13:E20","E",13,RED,"#9B3835");
info(21,"历史 PR 结果","",30);
info(22,"解释口径","同一场景优先采用最近的相关评审轮次。正式包本轮结果在冒烟表记录。",27);
onRange(summary,"A23").format.rowHeight=11;
section(summary,24,"正式包冒烟重点");
const focus=["正式安装包","","","","",""];
focus.forEach((item,i)=>{
  const row=25+i;
  onRange(summary,"A"+row).values=[[item]];
  merge(summary,"B"+row+":H"+row,i===0?"使用正式打包产物，记录版本和来源。后续小修按影响范围复验。":"");
  if(i%2===1)rowFill(summary,row,"I",BAND);
  styleText(summary,"A"+row,{bold:true,color:BLUE});
  styleText(summary,"I"+row,{color:MUTED});
  onRange(summary,"A"+row).format.rowHeight=36;
});
onRange(summary,"A31:I31").values=[["冒烟用例",null,"待执行",null,"通过",null,"失败／受阻",null,null]];
const numbered='--(LEN(TRIM('+caseId+'))>0)';
const countStatus=(state)=>'SUMPRODUCT('+numbered+',--('+caseState+'="'+state+'"))';
onRange(summary,"B31").formulas=[["=SUMPRODUCT("+numbered+")"]];
onRange(summary,"D31").formulas=[["="+countStatus("待执行")]];
onRange(summary,"F31").formulas=[["="+countStatus("通过")]];
onRange(summary,"H31").formulas=[["="+countStatus("失败")+"+"+countStatus("受阻")]];
onRange(summary,"I31").formulas=[['="不适用 "&'+countStatus("不适用")]];
rowFill(summary,31,"I",LIGHT);
onRange(summary,"C31:D31").format.fill=AMBER;
styleText(summary,"A31:I31",{size:11,bold:true,color:BLUE});
for(const address of ["B31","D31","F31","H31"])styleText(summary,address,{size:18,bold:true,color:address==="D31"?"#764611":BLUE});
onRange(summary,"B31:I31").format.horizontalAlignment="center";
onRange(summary,"A31").format.rowHeight=39;
flagPositive(summary,"H31","H",31,RED,"#9B3835");
const documented='--(LEN(TRIM(SUBSTITUTE('+actual+',"　"," ")))>0)';
const noNumber='--(LEN(TRIM('+caseId+'))=0)';
const duplicates='SUMPRODUCT('+numbered+',--(COUNTIF('+caseId+','+caseId+')>1))';
const orphaned='SUMPRODUCT('+noNumber+',--((('+caseState+'<>"")+('+actual+'<>"")+(ReleaseSmokeCases[需求]<>""))>0))';
const badIds='('+duplicates+'+'+orphaned+'>0)';
const resultCount='SUMPRODUCT('+numbered+','+documented+',--((('+caseState+'="通过")+('+caseState+'="不适用"))>0))';
const passed="AND($B$31>0,$F$31>0,$D$31=0,$H$31=0,NOT("+badIds+"),"+resultCount+"=$B$31)";
onRange(summary,"B3").formulas=[['=IF('+badIds+',"冒烟表有缺少编号或编号重复的记录，请核对后再判定。",IF('+passed+',"任务整体测试通过：适用的正式包冒烟用例全部通过。",IF(H31>0,"任务整体测试尚未通过：仍有失败或受阻的正式包冒烟用例。","阶段汇报：适用用例在正式打包产物上全部通过并回填证据后，判定任务整体测试通过。")))']];
onRange(summary,"A3:I3").conditionalFormats.addCustom("="+passed,{fill:GREEN,font:{color:"#2E624B"}});
onRange(summary,"A3:I3").conditionalFormats.addCustom("=OR($H$31>0,"+badIds+")",{fill:RED,font:{color:"#9B3835"}});
info(32,"整体通过判定","只计正式打包产物上的结果。每条用例有唯一编号，适用用例全部通过且证据已回填后，判定整体测试通过。不适用注明范围依据。",35);
section(summary,33,"配置、验证归档和责任田来源");
onRange(summary,"A34").values=[["来源编号"]];
merge(summary,"B34:D34","配置、提交或文档标题");
merge(summary,"E34:I34","链接或访问说明");
header(summary,"A34:I34");
for(let row=35;row<=42;row++){
  merge(summary,"B"+row+":D"+row,"");
  merge(summary,"E"+row+":I"+row,"");
  onRange(summary,"A"+row).format.rowHeight=25;
  if(row%2===0)rowFill(summary,row,"I",BAND);
}
workbook.recalculate();
const now=()=>onRange(summary,"B3").values[0][0];
if(onRange(summary,"B31").values[0][0]!==0||!now().startsWith("阶段汇报"))throw Error("空模板状态错误。");
if(process.argv.includes("--test")){
  const assertOutcome=(prefix)=>{
    workbook.recalculate();
    if(!now().startsWith(prefix))throw Error("摘要实际显示："+now()+"，预期："+prefix);
  };
  const row=(r,id,state,result)=>{onRange(cases,"C"+r).values=[[id]];onRange(cases,"O"+r+":P"+r).values=[[state,result]];};
  const waiting="阶段汇报", pass="任务整体测试通过", idIssue="冒烟表有缺少编号", noPass="任务整体测试尚未通过";
  assertOutcome(waiting);
  row(2,"T-01","待执行",null);
  row(3,null,"通过","残留结果");
  assertOutcome(idIssue);
  row(3,null,null,null);
  assertOutcome(waiting);
  row(2,"T-01","通过"," 　 ");
  assertOutcome(waiting);
  row(2,"T-01","通过","正式包证据");
  assertOutcome(pass);
  row(3,"T-01","通过","正式包证据");
  assertOutcome(idIssue);
  row(3,"T-02","不适用","范围确认");
  assertOutcome(pass);
  row(3,"T-02","不适用",null);
  assertOutcome(waiting);
  row(3,"T-02","受阻","试验环境不可达");
  assertOutcome(noPass);
  row(3,"T-02","失败","行为失败");
  assertOutcome(noPass);
  row(3,"T-02",null,null);
  assertOutcome(waiting);
  console.log("摘要回归通过：空表、无编号残留、编号重复、缺结果、待执行、有效通过、不适用、有失败或受阻。");
} else {
  await fs.mkdir(target,{recursive:true});
  const out=await SpreadsheetFile.exportXlsx(workbook);
  await out.save(path.join(target,"发布测试报告模板.xlsx"));
  for(const [sheetName,range,preview] of [["发布测试摘要","A1:I34","ccs-template-summary"],["证据截图","A1:M26","ccs-template-images"]]){
    const picture=await workbook.render({sheetName,range,scale:.9,format:"png"});
    await fs.writeFile(path.join(target,preview+".png"),new Uint8Array(await picture.arrayBuffer()));
  }
}

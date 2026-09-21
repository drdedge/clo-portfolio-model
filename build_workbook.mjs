// Local Excel renderer. Python owns ingestion, methodology arithmetic and simulation.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(path.join(process.env.CLO_ARTIFACT_MODULES||path.join(import.meta.dirname,'node_modules'),'_clo_resolver.cjs'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const [input,output,...extra]=process.argv.slice(2);
const packet=JSON.parse(await fs.readFile(input,'utf8'));
const {config:c,portfolio:p,analytics:a,concentration:conc,analysis:an}=packet;
const w=Workbook.create();
const names=['Read Me','Agency Comparison','Outputs','Portfolio Inputs','Assumptions','Portfolio Calc','Obligor Calc','Capital Calc','SP Credit Parameters','Concentration Calc','Fitch Inputs','Fitch Parameters','Fitch Calc','Stress Inputs','Cash Flow Calc','Sensitivity','Stress Results','Checks','Gaps and Sources','Methodology','Run Snapshot'];
const s=Object.fromEntries(names.map(n=>[n,w.worksheets.add(n)]));
const C={ink:'#243247',navy:'#203955',line:'#D7DFE7',blue:'#0000FF',green:'#008000',input:'#FFF4C9',python:'#EEF2F7',warn:'#FFF1DD'};
const F={num:'#,##0;(#,##0);"-"',pct:'0.0%;(0.0%);"-"',amount:'#,##0;(#,##0);"-"',decimal:'0.00',date:'yyyy-mm-dd'};
const clean=v=>typeof v==='string'&&/^[=+@-]/.test(v)?"'"+v:v;
const col=n=>{let z='';for(;n;n=Math.floor((n-1)/26))z=String.fromCharCode(65+(n-1)%26)+z;return z;};
function values(sh,cell,rows){if(rows.length)sh.getRange(cell).write(rows.map(row=>row.map(v=>v===undefined?null:clean(v))));}
function formula(sh,cell,f){sh.getRange(cell).formulas=[[f]];sh.getRange(cell).format.font.color=f.includes('!')||/\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b|\bSPWARF\b/.test(f)?C.green:'#000000';}
function title(sh,text,subtitle,last='L'){
  sh.showGridLines=false;
  sh.getRange(`A1:${last}8`).format.font={name:'Arial',size:11,color:C.ink};
  sh.getRange(`A:A`).format.columnWidth=2;sh.getRange(`B:B`).format.columnWidth=2;
  sh.getRange(`C:${last}`).format.columnWidth=16;
  sh.getRange('C2').values=[[text]];sh.getRange('C2').format.font={name:'Arial',size:17,bold:true,color:C.ink};
  sh.getRange(`C2:${last}2`).format.borders={bottom:{style:'thin',color:C.line}};
  sh.getRange('C3').values=[[subtitle]];sh.getRange('C3').format.font={name:'Arial',size:10,italic:true,color:C.ink};
  sh.getRange('3:3').format.rowHeight=22;
}
function header(sh,range,rows){sh.getRange(range).values=[rows];sh.getRange(range).format={fill:C.navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:38,verticalAlignment:'center'};}
function body(sh,range){sh.getRange(range).format.font={name:'Arial',size:11,color:C.ink};sh.getRange(range).format.rowHeight=21;}
function source(sh,range){sh.getRange(range).format.fill=C.python;}
function editable(sh,range){sh.getRange(range).format.fill=C.input;sh.getRange(range).format.font.color=C.blue;}
function status(sh,cell='C5'){formula(sh,cell,'=IF(Refresh_Required,"REFRESH REQUIRED — Python results reflect the last run","Python results match the imported inputs")');sh.getRange(cell).format.font={name:'Arial',size:11,bold:true,color:C.ink};}
function named(name,ref){w.names.add(name,ref);}
function checkformat(sh,range){sh.getRange(range).conditionalFormats.add('containsText',{text:'CHECK',format:{fill:'#FCE6DF'}});sh.getRange(range).conditionalFormats.add('containsText',{text:'REFRESH',format:{fill:'#FFF1DD'}});}
function dateValue(v){return v?new Date(v+'T00:00:00Z'):null;}
const fields=['instrument_id','obligor_id','obligor_name','par','sp_rating','sp_industry','country','seniority','rate_type','spread_bps','fixed_coupon_rate','floor_bps','maturity_date','recovery_aaa','price','payment_frequency','currency','benchmark'];
const data=p.facilities.length?p.facilities:[Object.fromEntries(fields.map(k=>[k,null]))];
const n=data.length,end=7+n;

// Raw source fields have a fixed schema; row count is rebuilt for every CSV.
for(const name of ['Portfolio Inputs','Run Snapshot']){
 const sh=s[name];sh.showGridLines=false;sh.getRange('A:Y').format.columnWidth=16;
 sh.getRange(`A1:Y${end}`).format.font={name:'Arial',size:10,color:C.ink};
 sh.getRange('A2').values=[[name==='Run Snapshot'?'Imported Portfolio Snapshot':'Portfolio Inputs']];sh.getRange('A2').format.font={name:'Arial',size:17,bold:true,color:C.ink};
 sh.getRange('A3').values=[[name==='Run Snapshot'?'Comparison baseline. Do not edit. Rebuild from CSV to change row count.':'Imported CSV fields. Edit the CSV for refresh; workbook edits flag Python results as stale.']];
 const hs=name==='Portfolio Inputs'?[...fields,'weight','term_years','floating_par_x_spread','par_x_recovery','input_changes','duplicate_id','field_errors','SP_rating_factor','par_x_SP_factor','par_x_SP_abs_deviation']:fields;
 header(sh,`A7:${col(hs.length)}7`,hs);
 values(sh,'A8',data.map(r=>fields.map(k=>k==='maturity_date'?dateValue(r[k]):r[k])));
 source(sh,`A8:R${end}`);
 sh.getRange('C:C').format.columnWidth=29;sh.getRange('F:F').format.columnWidth=31;sh.getRange('G:G').format.columnWidth=20;sh.getRange('A:B').format.columnWidth=19;
 sh.getRange(`D8:D${end}`).setNumberFormat(F.amount);
 for(const letter of ['K','N'])sh.getRange(`${letter}8:${letter}${end}`).setNumberFormat(F.pct);
 sh.getRange(`M8:M${end}`).setNumberFormat(F.date);
 sh.getRange(`O8:O${end}`).setNumberFormat(F.decimal);
 sh.getRange(`P8:P${end}`).setNumberFormat('0');
 sh.freezePanes.freezeRows(7);sh.freezePanes.freezeColumns(2);
}
const pin=s['Portfolio Inputs'];
for(let r=8;r<=end;r++){
 formula(pin,`S${r}`,`=IF(Portfolio_Par>0,D${r}/Portfolio_Par,"")`);
 formula(pin,`T${r}`,`=IF(A${r}="","",(M${r}-as_of_date)/365.25)`);
 formula(pin,`U${r}`,`=IF(I${r}="Floating",D${r}*J${r},0)`);
 formula(pin,`V${r}`,`=IF(A${r}="","",D${r}*N${r})`);
 formula(pin,`W${r}`,'='+fields.map((k,i)=>`IF(${col(i+1)}${r}='Run Snapshot'!${col(i+1)}${r},0,1)`).join('+'));
 formula(pin,`X${r}`,`=IF(A${r}="",0,COUNTIF($A$8:$A$${end},A${r})-1)`);
 formula(pin,`Y${r}`,`=IF(A${r}="",1,IF(OR(D${r}<=0,N${r}<0,N${r}>1,M${r}<=as_of_date),1,0))`);
 formula(pin,`Z${r}`,`=IF(A${r}="","",VLOOKUP(E${r},SP_WARF_Factors,2,FALSE))`);
 formula(pin,`AA${r}`,`=IF(A${r}="","",D${r}*Z${r})`);
 formula(pin,`AB${r}`,`=IF(A${r}="","",D${r}*ABS(Z${r}-SPWARF))`);
}
pin.getRange(`S8:S${end}`).setNumberFormat(F.pct);pin.getRange(`T8:T${end}`).setNumberFormat('0.00');pin.getRange(`U8:V${end}`).setNumberFormat(F.amount);
pin.getRange('Z:AB').format.columnWidth=23;pin.getRange(`Z8:AB${end}`).setNumberFormat(F.decimal);
pin.tables.add(`A7:AB${end}`,true,'PortfolioData');
named('Portfolio_Par',`'Portfolio Calc'!$D$8`);
named('SPWARF',`'Portfolio Calc'!$D$21`);named('SP_DRD',`'Portfolio Calc'!$D$23`);

// Agency parameter tables are source constants. They are not interchangeable.
const cq=packet.credit_quality, fp=packet.fitch;
const sp=s['SP Credit Parameters'];title(sp,'S&P Credit Parameters','Published factor-table basis. Performing assets rated AAA through CCC-.','F');
sp.getRange('C:C').format.columnWidth=19;sp.getRange('D:D').format.columnWidth=22;sp.getRange('E:E').format.columnWidth=5;sp.getRange('F:F').format.columnWidth=99;
header(sp,'C7:D7',['S&P input rating','Rating factor']);values(sp,'C8',Object.entries(cq.rating_factors));source(sp,'C8:D26');sp.getRange('D8:D26').setNumberFormat(F.decimal);named('SP_WARF_Factors',"'SP Credit Parameters'!$C$8:$D$26");
const spNotes=[['Calculation','SPWARF = SUM(par × rating factor) / eligible par. Default-rate dispersion is the par-weighted absolute deviation from SPWARF.'],['Scope','This engine accepts performing corporate assets AAA through CCC-. Unknown, unrated and defaulted assets fail validation; they do not receive a zero factor.'],['Meaning','Credit-quality description only. This factor scale is different from Fitch WARF. Neither metric is an AAA scenario default rate.'],['Table source',cq.source.table_source_title],['Source URL',cq.source.table_source_url],['Definition source',cq.source.definition_source_url],['Version basis',`Table reference ${cq.source.table_reference_date}; verified ${cq.source.verified_on}. Review transaction applicability.`],['Editing','Source constants are not scenario controls. Update the sourced Python table and rebuild to change versions; the reconciliation check detects edits here.']];
spNotes.forEach(([label,note],i)=>{values(sp,`F${7+i*2}`,[[label],[note]]);sp.getRange(`F${7+i*2}`).format.font.bold=true;sp.getRange(`F${8+i*2}`).format.wrapText=true;sp.getRange(`${8+i*2}:${8+i*2}`).format.rowHeight=47;});

// One authoritative editable scalar table, with an immutable run-value column.
const ash=s.Assumptions;title(ash,'Assumptions','Blue / amber = editable; grey = value used in the last Python run','H');
ash.tabColor='#E9DBC5';ash.getRange('C:C').format.columnWidth=39;ash.getRange('D:E').format.columnWidth=24;ash.getRange('F:F').format.columnWidth=17;ash.getRange('G:G').format.columnWidth=12;ash.getRange('H:H').format.columnWidth=71;
header(ash,'C7:H7',['Key / named range','Current value','Last run value','Unit','Changed','Provenance / meaning']);
const scalarKeys=['as_of_date','legal_final_date','currency','benchmark','base_senior_pct','equity_pct','senior_coupon_bps','junior_coupon_bps','senior_floor_pct','junior_floor_pct','senior_fee_bps','fixed_fee_per_period','subordinated_fee_bps','oc_trigger','ic_trigger','recovery_lag_quarters','annual_prepayment_rate','reinvestment_end_date','reinvestment_price','reinvestment_spread_bps','reinvestment_recovery','reinvestment_maturity_years','reinvestment_floor_bps','principal_support_interest','final_liquidation_price','oc_recovery_credit','reinvestment_stop_on_trigger','base_default_rate','base_scenario_id','agency_sdr_aaa','agency_sdr_source'];
const assumptionRows=scalarKeys.map(k=>({key:k,value:c[k],source:c.assumption_provenance[k]||'Fictional development assumption; review before use'}));
for(const sc of c.scenarios)for(const key of ['recovery_multiplier','annual_prepayment_rate'])assumptionRows.push({key:`scenario.${sc.id}.${key}`,value:sc[key],source:`Fictional ${sc.id} scenario input; overrides the global setting`});
function units(k){if(k.includes('date'))return 'date';if(k.includes('bps'))return 'bps / year';if(k.includes('lag'))return 'quarters';if(k.includes('years'))return 'years';if(k==='agency_sdr_aaa'||k.includes('pct')||k.includes('rate')||k.includes('recovery')&&!k.includes('multiplier')||k.includes('price'))return 'fraction';if(k.includes('trigger')||k.includes('multiplier'))return 'multiple';if(k.includes('fee_per'))return `${c.currency}/quarter`;return 'text / flag';}
let ar=8;
for(const r of assumptionRows){
 const u=units(r.key), v=r.key.endsWith('date')?dateValue(r.value):r.value;
 values(ash,`C${ar}`,[[r.key,v,v,u,null,r.source]]);formula(ash,`G${ar}`,`=IF(D${ar}=E${ar},0,1)`);
 if(u==='fraction')ash.getRange(`D${ar}:E${ar}`).setNumberFormat(F.pct);
 if(u==='date')ash.getRange(`D${ar}:E${ar}`).setNumberFormat(F.date);
 if(u==='multiple')ash.getRange(`D${ar}:E${ar}`).setNumberFormat('0.00"x"');
 named(r.key.replaceAll('.','_'),`'Assumptions'!$D$${ar}`);ar++;
}
body(ash,`C8:H${ar-1}`);editable(ash,`D8:D${ar-1}`);source(ash,`E8:E${ar-1}`);ash.getRange(`H8:H${ar-1}`).format.wrapText=true;ash.getRange(`C8:H${ar-1}`).format.rowHeight=32;ash.freezePanes.freezeRows(7);
ash.getRange(`D12`).dataValidation={rule:{type:'decimal',operator:'between',formula1:.6,formula2:.7}};

// Calendar-indexed default and rate paths, with precise change detection.
const stress=s['Stress Inputs'];stress.showGridLines=false;stress.getRange('A:I').format.columnWidth=19;stress.getRange('A:A').format.columnWidth=22;
stress.getRange('A2').values=[['Stress Timing And Interest Rates']];stress.getRange('A2').format.font={name:'Arial',size:17,bold:true};stress.getRange('A3').values=[['Default weights are fractions of total cumulative defaults. Rate paths are fictional development scenarios.']];
header(stress,'A7:I7',['Scenario','Period','Period end','Default weight','Index rate','Run weight','Run rate','Changed','Source']);
let sr=8;const stressBlocks=[];
for(const sc of c.scenarios){
 const start=sr, periods=Math.max(sc.default_weights.length,sc.index_rate_path.length);
 for(let i=0;i<periods;i++){
  const d=new Date(c.as_of_date+'T00:00:00Z');d.setUTCMonth(d.getUTCMonth()+3*(i+1));
  values(stress,`A${sr}`,[[sc.id,i+1,d,sc.default_weights[i]??0,sc.index_rate_path[Math.min(i,sc.index_rate_path.length-1)],sc.default_weights[i]??0,sc.index_rate_path[Math.min(i,sc.index_rate_path.length-1)],null,'Timing T20 / fictional rates']]);
  formula(stress,`H${sr}`,`=IF(D${sr}=F${sr},0,1)+IF(E${sr}=G${sr},0,1)`);sr++;
 }
 stressBlocks.push({sid:sc.id,start,end:sr-1});
}
body(stress,`A8:I${sr-1}`);stress.getRange(`C8:C${sr-1}`).setNumberFormat(F.date);stress.getRange(`D8:G${sr-1}`).setNumberFormat(F.pct);editable(stress,`D8:E${sr-1}`);source(stress,`F8:G${sr-1}`);stress.getRange('I:I').format.columnWidth=33;stress.freezePanes.freezeRows(7);stress.freezePanes.freezeColumns(2);

// Shared descriptive formulas and S&P published factor-table calculations.
const pc=s['Portfolio Calc'];title(pc,'Portfolio Calculations',`${c.currency}, full units. Weighted spread uses floating par only. Term is bullet maturity, not amortising WAL.`,'Q');
status(pc);
pc.getRange('C:C').format.columnWidth=34;pc.getRange('D:D').format.columnWidth=23;pc.getRange('G:G').format.columnWidth=40;pc.getRange('H:I').format.columnWidth=17;
header(pc,'C7:D7',['Metric','Excel formula result']);
const metrics=[['Portfolio par',`=SUM('Portfolio Inputs'!D8:D${end})`,F.amount],['Facilities',`=COUNTA('Portfolio Inputs'!A8:A${end})`,'0'],['Obligors',`=COUNTA('Obligor Calc'!A8:A${7+Math.max(1,a.obligors.length)})`,'0'],['Floating par',`=SUMIF('Portfolio Inputs'!I8:I${end},"Floating",'Portfolio Inputs'!D8:D${end})`,F.amount],['Floating share','=IF(D8>0,D11/D8,"")',F.pct],['Weighted spread (bps)','=IF(D11>0,SUM(\'Portfolio Inputs\'!U8:U'+end+')/D11,"")','0.0'],['Weighted stressed recovery','=IF(D8>0,SUM(\'Portfolio Inputs\'!V8:V'+end+')/D8,"")',F.pct],['Weighted remaining term (years)',`=IF(D8>0,SUMPRODUCT('Portfolio Inputs'!D8:D${end},'Portfolio Inputs'!T8:T${end})/D8,"")`,'0.00'],['Weighted price / 100',`=IF(D8>0,SUMPRODUCT('Portfolio Inputs'!D8:D${end},'Portfolio Inputs'!O8:O${end})/D8,"")`,'0.00'],['Largest obligor share',`=IF(D8>0,MAX('Obligor Calc'!H8:H${7+Math.max(1,a.obligors.length)}),"")`,F.pct],['Obligor HHI',`=IF(D8>0,SUM('Obligor Calc'!I8:I${7+Math.max(1,a.obligors.length)}),"")`,'0.0000'],['Effective obligors (1 / HHI)','=IF(D18>0,1/D18,"")','0.0'],['CCC category share',`=IF(D8>0,SUMIF('Portfolio Inputs'!E8:E${end},"CCC*",'Portfolio Inputs'!D8:D${end})/D8,"")`,F.pct],['S&P WARF (published factors)',`=IF(D8>0,SUM('Portfolio Inputs'!AA8:AA${end})/D8,"")`,F.decimal],['S&P AAA scenario default rate','=IF(Refresh_Required,"REFRESH REQUIRED",IF(ISNUMBER(agency_sdr_aaa),agency_sdr_aaa,"Unavailable"))',F.pct],['S&P default-rate dispersion',`=IF(D8>0,SUM('Portfolio Inputs'!AB8:AB${end})/D8,"")`,F.decimal]];
metrics.forEach(([label,value,fmt],i)=>{const r=8+i;values(pc,`C${r}`,[[label]]);if(value.startsWith('='))formula(pc,`D${r}`,value);else values(pc,`D${r}`,[[value]]);if(fmt)pc.getRange(`D${r}`).setNumberFormat(fmt);});
pc.getRange('D21').format.wrapText=true;pc.getRange('21:21').format.rowHeight=45;
let cr=7;
for(const [field,label] of [['sp_industry','Industry'],['sp_rating','Rating input'],['country','Country'],['seniority','Seniority'],['rate_type','Rate type']]){
 header(pc,`G${cr}:I${cr}`,[label,'Par','Share']);
 const entries=a.composition[field]||[], sourceCol=col(fields.indexOf(field)+1);
 for(const entry of entries){cr++;values(pc,`G${cr}`,[[entry.label]]);formula(pc,`H${cr}`,`=SUMIF('Portfolio Inputs'!${sourceCol}8:${sourceCol}${end},G${cr},'Portfolio Inputs'!D8:D${end})`);formula(pc,`I${cr}`,`=IF(Portfolio_Par>0,H${cr}/Portfolio_Par,"")`);pc.getRange(`H${cr}`).setNumberFormat(F.amount);pc.getRange(`I${cr}`).setNumberFormat(F.pct);}
 cr+=3;
}
pc.getRange(`G8:G${cr}`).format.wrapText=true;pc.getRange(`G8:I${cr}`).format.rowHeight=29;
if((a.composition.sp_industry||[]).length){
 const ce=7+Math.min(10,a.composition.sp_industry.length);
 const chart=pc.charts.add('bar',[pc.getRange(`G7:G${ce}`),pc.getRange(`I7:I${ce}`)]);
 chart.title='Largest Industries (% of Par)';chart.hasLegend=false;chart.barOptions.direction='bar';chart.setPosition('K7','S27');chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=12;chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};chart.yAxis={numberFormatCode:'0%',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};
}

// Obligor aggregation preserves facility rows while grouping common default entities.
const ob=s['Obligor Calc'];ob.showGridLines=false;ob.getRange('A:I').format.columnWidth=19;ob.getRange('B:B').format.columnWidth=30;ob.getRange('D:D').format.columnWidth=35;ob.getRange('A2').values=[['Obligor Calculations']];ob.getRange('A2').format.font={name:'Arial',size:17,bold:true};ob.getRange('A3').values=[['Identifiers and grouping come from Python; par, facility counts and concentration are Excel formulas.']];
header(ob,'A7:I7',['Obligor ID','Obligor name','Rating input','Industry','Country','Grouped par','Facilities','Weight','Weight squared']);
status(ob,'A5');
const obs=a.obligors.length?a.obligors:[{}];
obs.forEach((o,i)=>{const r=8+i;values(ob,`A${r}`,[[o.obligor_id,o.obligor_name,o.sp_rating,o.sp_industry,o.country]]);formula(ob,`F${r}`,`=IF(A${r}="","",SUMIF('Portfolio Inputs'!B8:B${end},A${r},'Portfolio Inputs'!D8:D${end}))`);formula(ob,`G${r}`,`=IF(A${r}="","",COUNTIF('Portfolio Inputs'!B8:B${end},A${r}))`);formula(ob,`H${r}`,`=IF(Portfolio_Par>0,F${r}/Portfolio_Par,"")`);formula(ob,`I${r}`,`=IF(Portfolio_Par>0,H${r}^2,"")`);});
body(ob,`A8:I${7+obs.length}`);source(ob,`A8:E${7+obs.length}`);ob.getRange(`F8:F${7+obs.length}`).setNumberFormat(F.amount);ob.getRange(`H8:H${7+obs.length}`).setNumberFormat(F.pct);ob.getRange(`I8:I${7+obs.length}`).setNumberFormat('0.00000');ob.freezePanes.freezeRows(7);ob.freezePanes.freezeColumns(2);

const capital=s['Capital Calc'];title(capital,'Capital Structure','Senior sensitivity: equity stays fixed; junior debt is the residual. Funding at par is a fictional assumption.','J');capital.getRange('C:C').format.columnWidth=22;
header(capital,'C7:J7',['Case','Senior share','Junior share','Equity share','Senior balance','Junior balance','Equity contribution','Stack difference']);
const capitalSizes=[['Base',null],...c.senior_sizes.map(v=>[`${Math.round(v*100)}% senior`,v])];
capitalSizes.forEach(([label,sz],i)=>{const r=8+i;values(capital,`C${r}`,[[label]]);if(sz===null)formula(capital,`D${r}`,'=base_senior_pct');else values(capital,`D${r}`,[[sz]]);formula(capital,`E${r}`,`=1-D${r}-F${r}`);formula(capital,`F${r}`,'=equity_pct');formula(capital,`G${r}`,`=Portfolio_Par*D${r}`);formula(capital,`H${r}`,`=Portfolio_Par*E${r}`);formula(capital,`I${r}`,`=Portfolio_Par*F${r}`);formula(capital,`J${r}`,`=SUM(G${r}:I${r})-Portfolio_Par`);});
capital.getRange('D8:F19').setNumberFormat(F.pct);capital.getRange('G8:J19').setNumberFormat(F.amount);named('Senior_Balance',"'Capital Calc'!$G$8");named('Junior_Balance',"'Capital Calc'!$H$8");named('Equity_Contribution',"'Capital Calc'!$I$8");
values(capital,'C23',[['Sizing controls are on Assumptions. Change percentages to change tranche balances.'],['A 64% senior balance plus 26% junior debt and 10% equity funds 100% of portfolio par.'],['Prices are descriptive; this prototype does not fund collateral at market value.']]);

// Public supplemental arithmetic, with all rating bands/industries available for audit.
const ct=s['Concentration Calc'];title(ct,'S&P Supplemental Concentration Tests','AAA is the test target. Loss arithmetic only; tranche sufficiency is not assessed.','L');ct.getRange('C:C').format.columnWidth=25;ct.getRange('D:D').format.columnWidth=29;ct.getRange('E:E').format.columnWidth=39;ct.getRange('F:L').format.columnWidth=18;status(ct);
header(ct,'C7:L7',['Test / route','Rating band','Industry','Required count','Selected count','Gross default par','Flat recovery','Loss (formula)','Loss / par','Selected IDs']);
const selected=['largest_obligor','primary_industry','alternative_industry'].map(k=>conc[k]).filter(Boolean);
const allCon=[...selected,...(conc.obligor_scenarios||[]),...(conc.primary_industry_scenarios||[]),...(conc.alternative_industry_scenarios||[])];
allCon.forEach((v,i)=>{let r=8+i;values(ct,`C${r}`,[[i<3?`Binding: ${v.test}`:v.test,v.rating_band,v.industry||'All industries',v.required_obligor_count,v.selected_obligor_count,v.gross_default_amount,v.recovery_rate,null,null,v.selected_obligor_ids.join(', ')]]);formula(ct,`J${r}`,`=H${r}*(1-I${r})`);formula(ct,`K${r}`,`=IF(Portfolio_Par>0,J${r}/Portfolio_Par,"")`);});
ct.getRange(`H8:H${Math.max(8,7+allCon.length)}`).setNumberFormat(F.amount);ct.getRange(`J8:J${Math.max(8,7+allCon.length)}`).setNumberFormat(F.amount);ct.getRange(`I8:I${Math.max(8,7+allCon.length)}`).setNumberFormat(F.pct);ct.getRange(`K8:K${Math.max(8,7+allCon.length)}`).setNumberFormat(F.pct);ct.getRange(`C8:E${Math.max(8,7+allCon.length)}`).format.wrapText=true;ct.getRange(`C8:L${Math.max(8,7+allCon.length)}`).format.rowHeight=39;ct.getRange('L:L').format.columnWidth=60;ct.freezePanes.freezeRows(7);

// Quarterly waterfall: Python rows plus independent formula reconcilations.
const cf=s['Cash Flow Calc'];const periods=an.base_run?.periods||[];const lastCF=col(4+Math.max(1,periods.length));
title(cf,'Development Cash Flow',`Python simulation; ${c.base_scenario_id}, ${(c.base_default_rate*100).toFixed(0)}% target defaults, ${(c.base_senior_pct*100).toFixed(0)}% senior. ACT/365.` ,lastCF);cf.getRange('C:C').format.columnWidth=34;cf.getRange('D:D').format.columnWidth=12;cf.getRange(`E:${lastCF}`).format.columnWidth=17;status(cf);
const cfkeys=['performing_begin','requested_defaults','defaults','prepayments','maturities','liquidated_par','purchased_par','performing_end','asset_interest_accrued','asset_interest_forfeited','asset_interest_receivable','asset_interest','recoveries_created','recovery_cash','recovery_receivable','liquidation_cash','principal_cash_begin','interest_cash_begin','senior_begin','junior_begin','senior_interest_due','senior_interest_paid','senior_interest_shortfall','senior_interest_arrears','junior_interest_due','junior_interest_paid','junior_interest_arrears','senior_fees_due','senior_fees_paid','senior_fee_arrears','sub_fees_due','sub_fees_paid','sub_fee_arrears','oc_numerator','oc_denominator','oc_ratio','ic_numerator','ic_denominator','ic_ratio','oc_triggered','ic_triggered','interest_diversion','senior_principal_paid','junior_principal_paid','senior_end','junior_end','equity_interest','equity_principal','reinvestment_cash','cash_end','cash_residual','par_residual','priority_violation'];
const cfr=Object.fromEntries(cfkeys.map((k,i)=>[k,8+i]));
header(cf,`C7:${lastCF}7`,['Cash flow line','Unit',...(periods.length?periods.map(r=>dateValue(r.date)):['Not run'])]);cf.getRange(`E7:${lastCF}7`).setNumberFormat('mmm-yy');
cfkeys.forEach((key,i)=>{const r=8+i;const isRatio=key.endsWith('_ratio'), isFlag=key.endsWith('_triggered');values(cf,`C${r}`,[[key.replaceAll('_',' '),isRatio?'multiple':isFlag?'TRUE/FALSE':c.currency,...periods.map(p=>p[key])]]);cf.getRange(`E${r}:${lastCF}${r}`).setNumberFormat(isRatio?'0.00"x"':isFlag?'General':F.amount);});
body(cf,`C8:${lastCF}${7+cfkeys.length}`);source(cf,`E8:${lastCF}${7+cfkeys.length}`);
const checkBase=63;
const cfCheckNames=['Cash sources','Cash uses','Cash conservation (Excel)','Collateral par roll-forward (Excel)','Senior debt roll-forward (Excel)','Junior debt roll-forward (Excel)','Coverage trigger disagreement','Waterfall priority violation (Excel)','Recovery receivable roll-forward','Asset interest receivable roll-forward'];
cfCheckNames.forEach((v,i)=>values(cf,`C${checkBase+i}`,[[v,i===6?'count':c.currency]]));
periods.forEach((p,i)=>{const z=col(5+i),prev=i?col(4+i):null;const r=k=>`${z}${cfr[k]}`;
 formula(cf,`${z}${checkBase}`,`=${r('principal_cash_begin')}+${r('interest_cash_begin')}+${r('asset_interest')}+${r('prepayments')}+${r('maturities')}+${r('recovery_cash')}+${r('liquidation_cash')}`);
 formula(cf,`${z}${checkBase+1}`,'='+['senior_fees_paid','senior_interest_paid','junior_interest_paid','sub_fees_paid','senior_principal_paid','junior_principal_paid','equity_interest','equity_principal','reinvestment_cash','cash_end'].map(r).join('+'));
 formula(cf,`${z}${checkBase+2}`,`=${z}${checkBase}-${z}${checkBase+1}`);
 formula(cf,`${z}${checkBase+3}`,`=${r('performing_begin')}-${r('defaults')}-${r('prepayments')}-${r('maturities')}-${r('liquidated_par')}+${r('purchased_par')}-${r('performing_end')}`);
 formula(cf,`${z}${checkBase+4}`,`=${r('senior_begin')}-${r('senior_principal_paid')}-${r('senior_end')}`);
 formula(cf,`${z}${checkBase+5}`,`=${r('junior_begin')}-${r('junior_principal_paid')}-${r('junior_end')}`);
 const tol=Math.max(.01,a.total_par*1e-10);
 formula(cf,`${z}${checkBase+6}`,`=ABS(IF(AND(${r('oc_denominator')}>${tol},${r('oc_numerator')}<oc_trigger*${r('oc_denominator')}),1,0)-IF(${r('oc_triggered')},1,0))+ABS(IF(AND(${r('ic_denominator')}>${tol},${r('ic_numerator')}<ic_trigger*${r('ic_denominator')}),1,0)-IF(${r('ic_triggered')},1,0))`);
 formula(cf,`${z}${checkBase+7}`,`=IF(OR(${r('senior_fee_arrears')}>${tol},${r('senior_interest_arrears')}>${tol}),${r('junior_interest_paid')}+${r('junior_principal_paid')}+${r('sub_fees_paid')}+${r('equity_interest')}+${r('equity_principal')},0)+IF(${r('senior_end')}>${tol},${r('junior_principal_paid')}+${r('equity_principal')},0)+IF(OR(${r('oc_triggered')},${r('ic_triggered')}),${r('equity_interest')},0)`);
 formula(cf,`${z}${checkBase+8}`,`=${prev?prev+cfr.recovery_receivable:'0'}+${r('recoveries_created')}-${r('recovery_cash')}-${r('recovery_receivable')}`);
 formula(cf,`${z}${checkBase+9}`,`=${prev?prev+cfr.asset_interest_receivable:'0'}+${r('asset_interest_accrued')}-${r('asset_interest_forfeited')}-${r('asset_interest')}-${r('asset_interest_receivable')}`);
});cf.getRange(`E63:${lastCF}72`).setNumberFormat(F.amount);cf.getRange('C63:C72').format.wrapText=true;cf.getRange('63:72').format.rowHeight=32;cf.freezePanes.freezeRows(7);cf.freezePanes.freezeColumns(4);

// Results grids are explicitly Python values. Gated displays prevent stale passes.
const sens=s.Sensitivity;title(sens,'Senior Sizing Sensitivity','Same portfolio and stress inputs at every size. Results are exploratory; AAA is not determined.','N');status(sens);sens.getRange('C:C').format.columnWidth=13;sens.getRange('D:E').format.columnWidth=18;sens.getRange('F:F').format.columnWidth=32;sens.getRange('G:H').format.columnWidth=24;sens.getRange('I:I').format.columnWidth=27;sens.getRange('J:N').format.columnWidth=19;
header(sens,'C7:N7',['Senior','Junior','Equity','Binding stress (see brackets)','Worst senior principal shortfall','Worst missed timely interest','All base-severity cases','Tested default rate','Scenario count','Run all pass','Run all valid','Run refresh']);
const sensitivities=an.sensitivities||[];
sensitivities.forEach((v,i)=>{const r=8+i;values(sens,`C${r}`,[[v.senior_pct,null,null,v.binding_scenario,v.senior_principal_shortfall,v.senior_timely_interest_shortfall,null,v.target_default_rate,c.scenarios.length,v.all_scenarios_pass,v.all_scenarios_valid]]);formula(sens,`D${r}`,`=1-C${r}-E${r}`);formula(sens,`E${r}`,'=equity_pct');formula(sens,`I${r}`,`=IF(Refresh_Required,"REFRESH REQUIRED",IF(M${r},IF(L${r},"Meets tested stresses","Shortfall"),"Target not attained"))`);formula(sens,`N${r}`,'=Refresh_Required');});
sens.getRange('C8:E18').setNumberFormat(F.pct);sens.getRange('F8:I18').format.wrapText=true;sens.getRange('8:18').format.rowHeight=33;sens.getRange('G8:H18').setNumberFormat(F.amount);sens.getRange('J8:J18').setNumberFormat(F.pct);checkformat(sens,'I8:I18');
header(sens,'P7:S7',['Last tested pass','First tested failure','Binding basis','Boundary status']);
sens.getRange('P:Q').format.columnWidth=22;sens.getRange('R:S').format.columnWidth=43;
sensitivities.forEach((v,i)=>values(sens,`P${8+i}`,[[v.boundary_lower,v.boundary_upper,v.binding_basis,v.boundary_status]]));
sens.getRange('P8:Q18').setNumberFormat(F.pct);sens.getRange('R8:S18').format.wrapText=true;sens.getRange('8:18').format.rowHeight=45;
header(sens,'C23:I23',['Senior','Scenario','Last tested pass','First tested failure','Boundary status','Unattainable targets','Non-monotonic']);
(an.boundaries||[]).forEach((v,i)=>values(sens,`C${24+i}`,[[v.senior_pct,v.scenario_id,v.lower_bound,v.upper_bound,v.status,v.has_infeasible_targets,v.non_monotonic]]));
sens.getRange(`C24:C${Math.max(24,23+(an.boundaries||[]).length)}`).setNumberFormat(F.pct);sens.getRange(`E24:F${Math.max(24,23+(an.boundaries||[]).length)}`).setNumberFormat(F.pct);sens.getRange(`G24:I${Math.max(24,23+(an.boundaries||[]).length)}`).format.wrapText=true;sens.getRange(`24:${Math.max(24,23+(an.boundaries||[]).length)}`).format.rowHeight=42;sens.freezePanes.freezeRows(7);
const results=s['Stress Results'];results.showGridLines=false;results.getRange('A:V').format.columnWidth=19;results.getRange('A2').values=[['Python Stress Results']];results.getRange('A2').format.font={name:'Arial',size:17,bold:true};results.getRange('A3').values=[['Detailed grid. Cash-flow pass means timely senior interest and ultimate principal under this exploratory run only.']];status(results,'A5');
const resultKeys=['senior_pct','scenario_id','target_default_rate','realized_default_rate','default_target_attained','senior_pass','senior_timely_interest_shortfall','senior_principal_shortfall','junior_interest_arrears','junior_principal_shortfall','equity_distributions','oc_breach_periods','ic_breach_periods','max_cash_residual','max_par_residual','max_priority_violation','accounting_valid','unallocated_defaults','stress_signature'];
header(results,'A7:S7',resultKeys);values(results,'A8',(an.stress_results||[]).map(v=>resultKeys.map(k=>v[k])));const re=7+Math.max(1,(an.stress_results||[]).length);body(results,`A8:S${re}`);source(results,`A8:S${re}`);results.getRange(`A8:A${re}`).setNumberFormat(F.pct);results.getRange(`C8:D${re}`).setNumberFormat(F.pct);results.getRange(`G8:K${re}`).setNumberFormat(F.amount);results.getRange('S:S').format.columnWidth=23;results.freezePanes.freezeRows(7);results.freezePanes.freezeColumns(2);if(an.stress_results?.length)results.tables.add(`A7:S${re}`,true,'StressResults');

// Fitch is an independent credit-input overlay, never an implicit S&P mapping.
const fi=s['Fitch Inputs'];fi.showGridLines=false;fi.getRange('A:X').format.columnWidth=20;
fi.getRange('A2').values=[['Fitch Facility Inputs']];fi.getRange('A2').format.font={name:'Arial',size:17,bold:true};
fi.getRange('A3').values=[['CSV source fields: edit the Fitch CSV and rerun with --fitch-inputs. Excel changes here are not imported by --assumptions-from.']];
fi.getRange('A4').values=[['Development proxies are labelled by row. Blank recovery or industry is missing information, not a zero assumption.']];status(fi,'A5');
const frs=fp.rows?.length?fp.rows:[{}], fe=7+frs.length;
header(fi,'A7:O7',['Facility ID','Par (shared)','Fitch IDR input','Rating basis','Fitch industry','Fitch recovery','Recovery basis','Source reference','Fitch rating factor','Par × factor','Par × recovery','Missing rating par','Missing recovery par','Changed cells','Missing industry par']);
header(fi,'Q7:X7',['Run ID','Run par','Run IDR','Run rating basis','Run industry','Run recovery','Run recovery basis','Run reference']);
frs.forEach((v,i)=>{const r=8+i,raw=[v.instrument_id,v.par,v.fitch_idr,v.fitch_rating_basis,v.fitch_industry,v.fitch_recovery,v.fitch_recovery_basis,v.source_reference];values(fi,`A${r}`,[raw]);values(fi,`Q${r}`,[raw]);
 formula(fi,`B${r}`,`=IF(A${r}="","",SUMIF('Portfolio Inputs'!A8:A${end},A${r},'Portfolio Inputs'!D8:D${end}))`);
 formula(fi,`I${r}`,`=IF(AND(C${r}<>"",OR(D${r}="public_fitch_idr",D${r}="reviewed_appendix5_equivalent",D${r}="development_proxy"),H${r}<>""),VLOOKUP(C${r},Fitch_WARF_Factors,2,FALSE),"")`);
 formula(fi,`J${r}`,`=IF(ISNUMBER(I${r}),B${r}*I${r},0)`);
 formula(fi,`K${r}`,`=IF(AND(A${r}<>"",M${r}=0),B${r}*F${r},0)`);
 formula(fi,`L${r}`,`=IF(A${r}="",0,IF(ISNUMBER(I${r}),0,B${r}))`);
 formula(fi,`M${r}`,`=IF(A${r}="",0,IF(AND(ISNUMBER(F${r}),F${r}>=0,F${r}<=1,OR(G${r}="fitch_issue_recovery_estimate",G${r}="fitch_issue_recovery_rating",G${r}="reviewed_bbsf_fallback",G${r}="development_assumption"),H${r}<>""),0,B${r}))`);
 formula(fi,`N${r}`,'='+Array.from({length:8},(_,j)=>`IF(${col(1+j)}${r}=${col(17+j)}${r},0,1)`).join('+'));
 formula(fi,`O${r}`,`=IF(A${r}="",0,IF(E${r}="",B${r},0))`);
});
source(fi,`A8:H${fe}`);source(fi,`Q8:X${fe}`);fi.getRange('D:D').format.columnWidth=29;fi.getRange('E:E').format.columnWidth=27;fi.getRange('G:H').format.columnWidth=55;fi.getRange(`D8:H${fe}`).format.wrapText=true;fi.getRange(`8:${fe}`).format.rowHeight=54;fi.getRange(`B8:B${fe}`).setNumberFormat(F.amount);fi.getRange(`F8:F${fe}`).setNumberFormat(F.pct);fi.getRange(`I8:I${fe}`).setNumberFormat('0.000');fi.getRange(`J8:M${fe}`).setNumberFormat(F.amount);fi.freezePanes.freezeRows(7);fi.freezePanes.freezeColumns(2);fi.tables.add(`A7:O${fe}`,true,'FitchFacilityData');
const ft=s['Fitch Parameters'];title(ft,'Fitch Credit Parameters','1 June 2026 criteria. WARF and WARR use different units and recovery bases from S&P.','G');
ft.getRange('C:C').format.columnWidth=18;ft.getRange('D:D').format.columnWidth=24;ft.getRange('E:E').format.columnWidth=5;ft.getRange('F:F').format.columnWidth=31;ft.getRange('G:G').format.columnWidth=95;
const ff=Object.entries(fp.factor_table);header(ft,'C7:D7',['Fitch IDR input','10-year PD factor']);values(ft,'C8',ff);source(ft,`C8:D${7+ff.length}`);ft.getRange(`D8:D${7+ff.length}`).setNumberFormat('0.000');named('Fitch_WARF_Factors',`'Fitch Parameters'!$C$8:$D$${7+ff.length}`);
const fitchURL='https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=structured-finance%2Fclos-corporate-cdos-rating-criteria-01-06-2026';
const fn=[['Criteria','CLOs and Corporate CDOs Rating Criteria, 1 June 2026. Replaces 21 July 2023.'],['WARF basis','Appendix 6: par-weighted 10-year default-rate factors. Displayed as factor points, e.g. B = 23.671. Do not compare this number directly with SPWARF.'],['WARR basis','Issue-level recovery estimate / recovery rating, or applicable BBsf recovery stress where required. The S&P recovery_aaa field is never reused automatically.'],['Example convention','The optional fictional sidecar labels each rating proxy and recovery fallback. Review the assumptions before replacing them with approved Fitch inputs.'],['Recovery coverage','Missing facility recoveries leave whole-portfolio WARR unavailable. Weighted sums of populated recoveries are helpers only, not a partial-portfolio WARR presented as complete.'],['Industry mapping','Fitch industry classification remains separate. No mapping is inferred from S&P labels. Missing industries prevent a complete PCM-ready dataset.'],['Default/loss hurdle','RDR and RLR require applicable Portfolio Credit Model analysis and documented inputs/version. They are not computed from WARF or WARR alone.'],['Cash-flow gap','Fitch timing, survivor-scaled amortisation, recovery lags and rate scenarios need implementation and benchmarking. Current development cash flows are not Fitch BDRs.'],['Public source',fitchURL],['Editing','Sourced constants: change the versioned code table and rebuild. These cells are not user assumption controls.']];
values(ft,'F7',fn);ft.getRange(`F7:G${6+fn.length}`).format.wrapText=true;ft.getRange(`7:${6+fn.length}`).format.rowHeight=65;source(ft,'G7:G16');
header(ft,'F20:G20',['Fallback classification','BBsf WARR factor']);values(ft,'F21',Object.entries(fp.recovery_table));source(ft,'F21:G32');ft.getRange('G21:G32').setNumberFormat(F.pct);ft.getRange('F21:F32').format.wrapText=true;ft.getRange('21:32').format.rowHeight=30;
const fc=s['Fitch Calc'];title(fc,'Fitch Portfolio Credit Calculations','Formula results require complete inputs for the metric. See source and development basis by facility.','F');status(fc);fc.getRange('C:C').format.columnWidth=38;fc.getRange('D:D').format.columnWidth=33;fc.getRange('E:E').format.columnWidth=5;fc.getRange('F:F').format.columnWidth=89;
header(fc,'C7:D7',['Metric','Result']);
const fcm=[['Shared portfolio par','=Portfolio_Par',F.amount],['Rating input coverage',`=IF(D8>0,1-SUM('Fitch Inputs'!L8:L${fe})/D8,"")`,F.pct],['Fitch WARF',`=IF(D8=0,"NOT RUN",IF(D9=1,SUM('Fitch Inputs'!J8:J${fe})/D8,"Missing rating inputs"))`,'0.000'],['Recovery input coverage',`=IF(D8>0,1-SUM('Fitch Inputs'!M8:M${fe})/D8,"")`,F.pct],['Fitch WARR',`=IF(D8=0,"NOT RUN",IF(D11=1,SUM('Fitch Inputs'!K8:K${fe})/D8,"Missing recovery inputs"))`,F.pct],['Industry input coverage',`=IF(D8>0,1-SUM('Fitch Inputs'!O8:O${fe})/D8,"")`,F.pct],['Fitch AAA RDR','NOT CALCULATED',null],['Fitch AAA RLR','NOT CALCULATED',null],['Fitch AAA result','NOT DETERMINED',null],['Edited Fitch source cells',`=SUM('Fitch Inputs'!N8:N${fe})`,'0'],['Edited Fitch factor cells','='+ff.map(([rating,value],i)=>`IF('Fitch Parameters'!C${8+i}="${rating}",0,1)+IF('Fitch Parameters'!D${8+i}=${value},0,1)`).join('+'),'0']];
fcm.forEach(([label,v,fmt],i)=>{const r=8+i;values(fc,`C${r}`,[[label]]);if(v.startsWith('='))formula(fc,`D${r}`,v);else values(fc,`D${r}`,[[v]]);if(fmt)fc.getRange(`D${r}`).setNumberFormat(fmt);});
const fcn=[['Rating status',fp.warf_status],['Recovery status',fp.warr_status],['Input source',fp.source_name||'No Fitch CSV supplied'],['What to update','Use templates/fitch_inputs_template.csv. Match instrument IDs to the portfolio CSV. Supply separately reviewed IDR basis, recovery basis, industry and source reference.'],['What is live','Factors, weighted sums, coverage, WARF and WARR recalculate in Excel. The comparison page flags edits until the authoritative CSV is rerun.'],['What is missing','An agency result also needs a complete credit dataset, PCM RDR/RLR, agency-specific cash-flow implementation and deal-level review.']];
fcn.forEach(([label,note],i)=>{values(fc,`F${7+i*2}`,[[label],[note]]);fc.getRange(`F${7+i*2}`).format.font.bold=true;fc.getRange(`F${8+i*2}`).format.wrapText=true;fc.getRange(`${8+i*2}:${8+i*2}`).format.rowHeight=58;});
fc.getRange('D8:D18').format.wrapText=true;named('Fitch_WARF',"'Fitch Calc'!$D$10");named('Fitch_WARR',"'Fitch Calc'!$D$12");
formula(fc,'D17',`=SUM('Fitch Inputs'!N8:N${fe})+ABS(COUNTA('Fitch Inputs'!A8:A1048576)-${fp.rows?.length||0})`);
values(sp,'C29',[['Edited source constants']]);formula(sp,'D29','='+Object.entries(cq.rating_factors).map(([rating,value],i)=>`IF(C${8+i}="${rating}",0,1)+IF(D${8+i}=${value},0,1)`).join('+'));named('SP_Parameter_Changes',"'SP Credit Parameters'!$D$29");

// Checks have independent equations and a visible stale control.
const ck=s.Checks;title(ck,'Validation And Reconciliation','Excel checks are live. Python checks reflect the last validated run.','H');ck.getRange('C:C').format.columnWidth=42;ck.getRange('D:F').format.columnWidth=23;ck.getRange('G:H').format.columnWidth=33;
header(ck,'C7:H7',['Check','Actual / difference','Tolerance / expected','Result','Owner','Meaning']);
let checks=[
 ['Portfolio source completeness',`=${packet.template?1:0}`,0,'Input validation','Python rejects missing or invalid inputs'],
 ['Duplicate facility identifiers',`=SUM('Portfolio Inputs'!X8:X${end})`,0,'Excel','Repeated obligor IDs are expected'],
 ['Portfolio par vs imported par',`=Portfolio_Par-${a.total_par}`,Math.max(.01,a.total_par*1e-10),'Excel','Reconcile imported balances'],
 ['Obligor grouped par vs portfolio',`=SUM('Obligor Calc'!F8:F${7+obs.length})-Portfolio_Par`,Math.max(.01,a.total_par*1e-10),'Excel','Every facility included once'],
 ['Obligor grouped count vs facilities',`=SUM('Obligor Calc'!G8:G${7+obs.length})-'Portfolio Calc'!D9`,0,'Excel','No missing facility group'],
 ['Capital stack difference',"='Capital Calc'!J8",Math.max(.01,a.total_par*1e-10),'Excel','Senior + junior + equity = par'],
 ['Edited portfolio cells',`=SUM('Portfolio Inputs'!W8:W${end})`,0,'Excel','Any source change requires rerun'],
 ['Edited scalar assumptions',`=SUM('Assumptions'!G8:G${ar-1})`,0,'Excel','Compare all editable scalar inputs'],
 ['Edited stress curve cells',`=SUM('Stress Inputs'!H8:H${sr-1})`,0,'Excel','Compare default weights and rate paths'],
 ['Added / deleted source rows',`=COUNTA('Portfolio Inputs'!A:A)-${(packet.template?0:n)+4}`,0,'Excel','Rebuild workbook to change portfolio row count'],
 ['Portfolio field sanity',`=SUM('Portfolio Inputs'!Y8:Y${end})`,0,'Excel','Full validation runs in Python'],
 ['Cash conservation (all grid runs)',an.stress_results?.length?Math.max(...an.stress_results.map(x=>x.max_cash_residual)):null,Math.max(.01,a.total_par*1e-10),'Python','Maximum absolute residual'],
 ['Waterfall priority (all grid runs)',an.stress_results?.length?Math.max(...an.stress_results.map(x=>x.max_priority_violation)):null,Math.max(.01,a.total_par*1e-10),'Python','Subordinate payments while senior due'],
 ['Accounting failures (all grid runs)',an.stress_results?.length?an.stress_results.filter(x=>!x.accounting_valid).length:null,0,'Python','Distinct from stress shortfalls'],
 ['Unattained default targets (grid)',an.stress_results?.length?an.stress_results.filter(x=>!x.default_target_attained).length:null,null,'Python','Disclosure: cannot treat these as a pass'],
 ['Five-year pattern WAM scope',packet.template?null:(a.weighted_term>=4&&a.weighted_term<=7?0:1),0,'Python','4–7 years typical; otherwise review timing'],
];
for(let i=0;i<10;i++){const row=checkBase+i;if(i<2)continue;checks.push([cfCheckNames[i],periods.length?`=MAX(MAX('Cash Flow Calc'!E${row}:${lastCF}${row}),-MIN('Cash Flow Calc'!E${row}:${lastCF}${row}))`:null,i===6?0:Math.max(.01,a.total_par*1e-10),'Excel','Independent base cash-flow equation']);}
let kr=8;
checks.push(['Edited Fitch input cells',"='Fitch Calc'!D17",0,'Excel','Change the source CSV and rerun'],['Edited Fitch source factors',"='Fitch Calc'!D18",0,'Excel','Versioned source constants must match'],['Edited S&P source factors','=SP_Parameter_Changes',0,'Excel','Versioned source constants must match'],['S&P WARF vs Python',packet.template?null:`=SPWARF-${cq.spwarf}`,0.000001,'Excel / Python','Independent weighted calculation'],['S&P dispersion vs Python',packet.template?null:`=SP_DRD-${cq.default_rate_dispersion}`,0.000001,'Excel / Python','Weighted absolute deviation'],['Fitch WARF vs Python',fp.warf==null?null:`=IF(ISNUMBER(Fitch_WARF),Fitch_WARF-${fp.warf},1)`,0.000001,'Excel / Python','Only compared when complete'],['Fitch WARR vs Python',fp.warr==null?null:`=IF(ISNUMBER(Fitch_WARR),Fitch_WARR-${fp.warr},1)`,0.000001,'Excel / Python','Only compared when complete']);
for(const [label,actual,tolerance,owner,note] of checks){values(ck,`C${kr}`,[[label,null,tolerance,null,owner,note]]);if(typeof actual==='string'&&actual.startsWith('='))formula(ck,`D${kr}`,actual);else values(ck,`D${kr}`,[[actual]]);formula(ck,`F${kr}`,tolerance===null?`=IF(ISNUMBER(D${kr}),"DISCLOSURE","NOT RUN")`:`=IF(ISNUMBER(D${kr}),IF(ABS(D${kr})<=E${kr},"OK","CHECK"),"NOT RUN")`);kr++;}
const refreshRow=kr+2;values(ck,`C${refreshRow}`,[['Refresh required']]);formula(ck,`D${refreshRow}`,`=IFERROR(OR(D8<>0,D14<>0,D15<>0,D16<>0,D17<>0,'Fitch Calc'!D17<>0,'Fitch Calc'!D18<>0,SP_Parameter_Changes<>0),TRUE)`);named('Refresh_Required',`'Checks'!$D$${refreshRow}`);
values(ck,`C${refreshRow+1}`,[['Live formula errors']]);formula(ck,`D${refreshRow+1}`,`=SUMPRODUCT(--ISERROR('Portfolio Calc'!D8:D23))+SUMPRODUCT(--ISERROR('Capital Calc'!D8:J19))+SUMPRODUCT(--ISERROR('Portfolio Inputs'!S8:AB${end}))+SUMPRODUCT(--ISERROR('Cash Flow Calc'!E63:${lastCF}72))+SUMPRODUCT(--ISERROR('Fitch Inputs'!I8:O${fe}))+SUMPRODUCT(--ISERROR('Fitch Calc'!D8:D18))+SUMPRODUCT(--ISERROR('Agency Comparison'!D8:G29))`);
formula(ck,`F${refreshRow+1}`,`=IF(D${refreshRow+1}=0,"OK","CHECK")`);body(ck,`C8:H${refreshRow+1}`);ck.getRange(`D8:E${refreshRow+1}`).setNumberFormat('#,##0.0000');ck.getRange(`H8:H${refreshRow+1}`).format.wrapText=true;ck.getRange(`C8:H${refreshRow+1}`).format.rowHeight=32;checkformat(ck,`F8:F${refreshRow+1}`);

const out=s.Outputs;title(out,'Portfolio And Development Results','Fictional development portfolio. S&P public criteria components plus exploratory cash flows.','J');out.getRange('C:C').format.columnWidth=43;out.getRange('D:D').format.columnWidth=28;out.getRange('F:J').format.columnWidth=22;status(out);
header(out,'C7:D7',['Portfolio summary','Result']);
[['Portfolio par',"='Portfolio Calc'!D8",F.amount],['Facilities',"='Portfolio Calc'!D9",'0'],['Obligors',"='Portfolio Calc'!D10",'0'],['Weighted floating spread (bps)',"='Portfolio Calc'!D13",'0.0'],['Supplied stressed recovery',"='Portfolio Calc'!D14",F.pct],['Weighted term (years)',"='Portfolio Calc'!D15",'0.00'],['Largest obligor share',"='Portfolio Calc'!D17",F.pct],['Base senior balance','=Senior_Balance',F.amount],['Base junior balance','=Junior_Balance',F.amount],['Equity contribution','=Equity_Contribution',F.amount]].forEach(([label,f,fmt],i)=>{values(out,`C${8+i}`,[[label]]);formula(out,`D${8+i}`,f);out.getRange(`D${8+i}`).setNumberFormat(fmt);});
if(packet.template)for(const r of [8,11,12,13,14,15,16,17])formula(out,`D${r}`,'="NOT RUN"');
header(out,'C21:D21',['Methodology / cash flow','Result']);
values(out,'C22',[['S&P AAA result','NOT DETERMINED'],['Agency scenario default rate',null],['Exploratory base cash flow',null],['Senior missed timely interest',null],['Senior final principal shortfall',null],['Supplemental test sufficiency','NOT ASSESSED']]);
formula(out,'D23','=IF(Refresh_Required,"REFRESH REQUIRED",IF(ISNUMBER(agency_sdr_aaa),agency_sdr_aaa,"Unavailable"))');out.getRange('D23').setNumberFormat(F.pct);
const base=an.base_run?.summary||{};
values(out,'G8',[['Python run values','Value'],['Base senior pass',base.senior_pass],['Missed timely interest',base.senior_timely_interest_shortfall],['Final senior principal',base.senior_principal_shortfall],['Realized default rate',base.realized_default_rate],['Target attained',base.default_target_attained]]);
const baseSensitivity=sensitivities.find(v=>v.senior_pct===c.base_senior_pct)||{};
values(out,'G14',[['Last tested pass',baseSensitivity.boundary_lower],['First tested failure',baseSensitivity.boundary_upper]]);out.getRange('H14:H15').setNumberFormat(F.pct);
values(out,'C28',[['Exploratory grid: last tested pass'],['Exploratory grid: first tested failure']]);
formula(out,'D28',packet.template?'="NOT RUN"':'=IF(Refresh_Required,"REFRESH REQUIRED",IF(ISNUMBER(H14),H14,"Unavailable"))');
formula(out,'D29',packet.template?'="NOT RUN"':'=IF(Refresh_Required,"REFRESH REQUIRED",IF(ISNUMBER(H15),H15,"Unavailable"))');out.getRange('D28:D29').setNumberFormat(F.pct);
formula(out,'D24',packet.template?'="NOT RUN"':'=IF(Refresh_Required,"REFRESH REQUIRED",IF(H13,IF(H9,"Meets tested case","Shortfall"),"Target not attained"))');
formula(out,'D25',packet.template?'="NOT RUN"':'=IF(Refresh_Required,"REFRESH REQUIRED",H10)');formula(out,'D26',packet.template?'="NOT RUN"':'=IF(Refresh_Required,"REFRESH REQUIRED",H11)');out.getRange('D25:D26').setNumberFormat(F.amount);out.getRange('H10:H11').setNumberFormat(F.amount);out.getRange('H12').setNumberFormat(F.pct);out.getRange('D22:D27').format.wrapText=true;out.getRange('22:27').format.rowHeight=32;source(out,'H9:H13');
values(out,'C31',[['Review sequence'],['1. Check inputs, mappings and assumption provenance.'],['2. Review Portfolio Calc and common-obligor grouping.'],['3. Review senior sensitivities, target attainment and cash flows.'],['4. Review all Checks and Methodology limitations before using results.']]);

const read=s['Read Me'];title(read,'Start Here','Version 0.2.0 — one portfolio, distinct S&P and Fitch calculations, explicit development assumptions.','E');
read.getRange('C:C').format.columnWidth=25;read.getRange('D:D').format.columnWidth=30;read.getRange('E:E').format.columnWidth=100;
header(read,'C7:E7',['Step / topic','Open or update','What to do']);
const readRows=[
 ['1. Start with results','Agency Comparison','See the S&P and Fitch columns together. Read the basis beside each metric. Missing / not calculated means further work is required; it is never a pass.'],
 ['2. Supply the portfolio','templates/portfolio_template.csv','One row per facility; keep common obligor IDs consistent. See docs/data_dictionary.md. Replace the CSV, not rows inside Excel. Row counts resize automatically on rerun.'],
 ['3. Supply Fitch inputs','templates/fitch_inputs_template.csv','Optional separate CSV, matched by instrument_id. Supply reviewed Fitch rating, rating basis, industry, recovery and source. Omit it for an S&P-only run; Fitch then displays missing inputs.'],
 ['4. Review deal assumptions','Assumptions; config/model.json','Confirm dates, coupons, fees, 64% senior / 26% junior / 10% equity, triggers, recoveries and reinvestment. The supplied terms and fictional development choices are labelled by row.'],
 ['5. Review stress assumptions','Stress Inputs','Default timing is S&P Table 20 informed. Rates, recovery lag and other deal controls are development assumptions. These cash flows do not implement a Fitch stress set.'],
 ['6. Run the example','From the package folder','python -m clo --portfolio examples/example.csv --fitch-inputs examples/fitch_example.csv --config config/model.json --output examples/Example_CLO.xlsx'],
 ['7. Replace and rerun','Use your new CSV paths','Change --portfolio and optional --fitch-inputs, then choose a fresh --output filename. See QUICK_START.md for the replacement example and the Windows launcher.'],
 ['8. Check the run','Checks','Resolve input, reconciliation and formula errors before interpreting results. Unattained default targets cannot count as passes. A blank template shows NOT RUN.'],
 ['9. Read the details','Outputs; Sensitivity; Cash Flow Calc','These are development cash-flow results. Review shortfalls, default target attainment and tested default brackets. An absence of shortfalls does not establish an agency rating.'],
 ['10. Save Excel assumptions','Blue cells; then --assumptions-from','Edit designated Assumptions / Stress Inputs cells, save, and rerun with --assumptions-from your_saved_workbook.xlsx. This flag does not import Portfolio Inputs, Fitch Inputs or parameter-table edits.'],
 ['Live Excel calculations','Portfolio / agency / capital tabs','Composition, grouping, SPWARF, S&P dispersion, Fitch WARF/WARR, coverage and reconciliation formulas recalculate. Results retain their stated input basis.'],
 ['Rerun-dependent results','Grey source / Python cells','Cash-flow simulations, sensitivities and selected concentration exposures reflect the last run. Input changes visibly flag REFRESH REQUIRED. Use automatic Excel calculation.'],
 ['Preserve source changes','Portfolio and Fitch source CSVs','Editing imported Excel fields is temporary. To keep a source change, update the authoritative CSV and rerun. Parameter tables are versioned source constants, not assumption controls.'],
 ['Agency metrics differ','S&P blue / Fitch purple tabs','S&P WARF and Fitch WARF use different scales. Supplied recovery_aaa is not Fitch WARR. An S&P SDR and Fitch RDR/RLR require separate credit-model analysis.'],
 ['Missing model components','Gaps and Sources','No S&P or Fitch agency rating is produced. S&P SDR and Fitch PCM outputs are missing; Fitch cash-flow rules and full S&P stresses remain engineering / calibration work.'],
 ['Fictional example basis','Input provenance','The 282-row sample comes from the supplied fictional workbook. Fitch rating equality proxies and first-lien recovery fallbacks are explicit development assumptions, not Fitch opinions.'],
 ['Tab colours','Purpose, not approval status','Teal: combined / development outputs. Grey: shared portfolio and structure. Gold: deal inputs. Blue: S&P. Purple: Fitch. Orange: development stresses / cash flows. Red: checks. Navy: guides.'],
 ['Cell colours','Source / input / formula','Grey fill = source or Python value. Amber fill + blue font = editable assumption. Black = same-sheet formula; green = cross-sheet formula. Read labels as well as colours.'],
 ['Local environment','README.md setup','Processing is local. Python and the Excel renderer must be provisioned in the approved FT environment. No real portfolio should leave that environment.'],
 ['For a new LLM / maintainer','docs/LLM_HANDOVER.md','Read the handover, methodology register, input dictionaries and tests. It identifies the authoritative files, calculation ownership, unresolved work and validation procedure.'],
 ['Run ID',packet.run_id,'Use this with the results JSON and validation report to identify the exact run.'],
 ['Portfolio source',p.source_name,p.source_hash],
 ['Fitch source',fp.source_name||path.basename(fp.source_path||'')||'Not supplied',fp.source_hash||'Not supplied'],
 ['Configuration / generated',packet.generated_at.slice(0,19).replace('T',' ')+' UTC',packet.config_hash]
];
values(read,'C8',readRows);body(read,`C8:E${7+readRows.length}`);read.getRange(`C8:E${7+readRows.length}`).format.wrapText=true;read.getRange(`8:${7+readRows.length}`).format.rowHeight=58;read.freezePanes.freezeRows(7);

const meth=s.Methodology;title(meth,'Methodology And Sources','Requirements are distinguished from supplied inputs, supported calculations and model gaps.','G');meth.getRange('C:C').format.columnWidth=29;meth.getRange('D:D').format.columnWidth=49;meth.getRange('E:E').format.columnWidth=58;meth.getRange('F:F').format.columnWidth=53;meth.getRange('G:G').format.columnWidth=80;
header(meth,'C7:G7',['Component','Implemented / result','Inputs / dependency','Gap or limitation','Source']);
const url=packet.methodology.url;
const methodRows=[
 ['Core criteria version','2019-06-21 / republished 2026-04-10','User supplied 66-page PDF; current public S&P page','S&P component basis. Fitch uses its own 1 June 2026 criteria and separate tabs',url],
 ['Portfolio credit analysis','Composition, obligor concentration, weighted terms/spreads/recoveries','Supplied issuer rating inputs, par, maturity, industry','Published SPWARF factors implemented. CDO Evaluator distribution and full CDO Monitor remain outstanding',url+' (paragraphs 68–101)'],
 ['Scenario default rates','Unavailable unless an external SDR is explicitly supplied','CDO Evaluator input/output, approved credit mapping and documented portfolio hash','No substitute percentile or concentration heuristic represented as S&P SDR',url+' (paragraphs 24–58)'],
 ['Cash-flow default capacity','Exploratory fixed-severity grid with first-failure brackets','Facility cash flows, stated fictional deal terms and scenario paths','Pro rata fractional defaults; not S&P Cash Flow Evaluator output or agency BDR',url+' (paragraphs 124–150)'],
 ['Default timing','Four five-year Table 20 patterns; quarterly allocation','Annual weights / 4; original par default notional','Review applicability for WAM outside 4–7 years and reinvesting portfolios',url+' (Table 20, paragraphs 130–133)'],
 ['Rates and prepayments','Explicit editable quarterly rates and annual prepayment fractions','Fictional low 0.5%, flat 3%, high 6% reference paths','Calibrated five-path CIR stresses / forward curve absent; no benchmark basis model','https://www.spglobal.com/ratings/en/regulatory/ratings-criteria'],
 ['Largest obligor test','Maximum loss across rating bands and prescribed counts','Common-default obligor groups; 5% flat corporate recovery','Performing corporate scope only; below CCC- and sovereigns excluded',url+' (Table 4, paragraphs 156–161)'],
 ['Largest industry tests','Primary 17% recovery; alternative rating-band counts / 5% recovery','Industry labels require reviewed official classification','Primary OR alternative route. Loss amounts do not establish tranche sufficiency',url+' (paragraphs 162–164)'],
 ['Recovery assumptions','Facility recovery_aaa used as supplied fictional stress inputs','No silent replacement or automatic Table 15 selection','Recovery-rating hierarchy, cov-lite status, debt cushion and jurisdiction mapping require review',url+' (paragraphs 109–123)'],
 ['Coverage tests','Editable senior OC/IC, cash diversion and reinvestment stop','Explicit simple performing-par numerator, optional recovery credit','No CCC haircut, discounted-obligation adjustments, junior tests, or indenture-specific definitions','Fictional development assumptions; see docs/cashflow_design.md'],
 ['Coupons and maturity','Quarterly/semiannual assets; quarterly notes; ACT/365','Synthetic as-of coupon anchor; contractual bullet maturities','No next-coupon dates, accrued purchase interest, day-count election or amortisation input','Supplied schema + explicit fictional timing convention'],
 ['Full rating scope','AAA NOT DETERMINED','Credit analysis + payment structure + counterparty/legal/operational review','Qualitative/legal/manager/counterparty criteria not implemented',url],
];
values(meth,'C8',methodRows);body(meth,`C8:G${7+methodRows.length}`);meth.getRange(`C8:G${7+methodRows.length}`).format.wrapText=true;meth.getRange(`8:${7+methodRows.length}`).format.rowHeight=73;meth.freezePanes.freezeRows(7);

// The shared page keeps agency hurdles distinct from independent cash-flow work.
const comp=s['Agency Comparison'];title(comp,'S&P And Fitch Comparison','Same portfolio and capital structure. Different credit metrics, stress conventions and outstanding requirements.','F');status(comp);
comp.getRange('C:C').format.columnWidth=32;comp.getRange('D:E').format.columnWidth=36;comp.getRange('F:F').format.columnWidth=75;
header(comp,'C7:F7',['Metric / question','S&P','Fitch','How to read this']);
const gated=f=>packet.template?'="NOT RUN"':`=IF(Refresh_Required,"REFRESH REQUIRED",${f})`;
const compRows=[
 ['Criteria basis','2019-06-21; republished 2026-04-10','2026-06-01','See Methodology, SP Credit Parameters and Fitch Parameters for sources and implemented scope.'],
 ['Weighted-average rating factor',gated('SPWARF'),gated('Fitch_WARF'),'Different scales: compare each against its own methodology. The Fitch example uses labelled development rating proxies.'],
 ['Credit input basis','Supplied fictional S&P ratings',fp.warf_status,'A public factor table does not verify the underlying rating or establish a target rating.'],
 ['Weighted recovery',gated("'Portfolio Calc'!D14"),gated('Fitch_WARR'),'S&P column is supplied fictional recovery_aaa. Fitch WARR requires separate issue recovery / BBsf basis. These are not like-for-like stressed recoveries.'],
 ['Recovery input coverage',gated('1'),gated("'Fitch Calc'!D11"),'Coverage means supplied required inputs, not agency validation. Fitch WARR stays unavailable until every facility has the required recovery basis.'],
 ['AAA default hurdle',gated('IF(ISNUMBER(agency_sdr_aaa),agency_sdr_aaa,"SDR not supplied")'),'RDR not calculated','SDR / RDR are gross default hurdles. Obtain the applicable credit-model outputs or complete and benchmark an independent implementation.'],
 ['AAA portfolio loss hurdle','Not a substitute for SDR','RLR not calculated','Fitch rating loss rate comes from PCM analysis. WARF multiplied by a loss assumption is not a replacement.'],
 ['Agency cash-flow BDR','Not implemented / benchmarked','Not implemented / benchmarked','Current development cash flows below must not be labelled agency BDRs. Fitch needs additional collateral and stress mechanics.'],
 ['Supplemental / concentration','Public S&P loss arithmetic','Not implemented','S&P event-loss amounts are on Concentration Calc; tranche sufficiency remains unassessed. Fitch industry taxonomy still needs review.'],
 ['AAA target conclusion','NOT DETERMINED','NOT DETERMINED','No rating or agency sufficiency conclusion is produced by this workbook.']
];
compRows.forEach((row,i)=>row.forEach((v,j)=>{const cell=`${col(3+j)}${8+i}`;if(typeof v==='string'&&v.startsWith('='))formula(comp,cell,v);else values(comp,cell,[[v]]);}));
comp.getRange('C8:F17').format.wrapText=true;comp.getRange('8:17').format.rowHeight=57;comp.getRange('D9:E9').setNumberFormat(F.decimal);comp.getRange('D11:E13').setNumberFormat(F.pct);
header(comp,'C20:F20',['Development cash flow','Result','Structure / severity','Interpretation']);
values(comp,'C21',[['Base senior interest / principal',null,`${c.base_senior_pct*100}% senior; ${c.base_default_rate*100}% defaults`,'Exploratory independent waterfall, S&P-informed timing and fictional rates / deal assumptions.']]);formula(comp,'D21',gated("Outputs!D24"));
values(comp,'C22',[['Last tested all-scenario pass',null,'Fixed grid, 5% default steps','Not an exact BDR. Review target attainment and each scenario boundary in Sensitivity.']]);formula(comp,'D22',gated('Outputs!D28'));comp.getRange('D22').setNumberFormat(F.pct);
values(comp,'C23',[['First tested scenario failure',null,'Same collateral at every size','Senior sensitivity is 60%–70%, equity fixed at 10%, junior debt adjusts.']]);formula(comp,'D23',gated('Outputs!D29'));comp.getRange('D23').setNumberFormat(F.pct);comp.getRange('C21:F23').format.wrapText=true;comp.getRange('21:23').format.rowHeight=45;
header(comp,'C26:G26',['Development gross defaults','Scenarios attaining target','Scenarios passing senior','Worst missed interest','Worst final principal shortfall']);
comp.getRange('G:G').format.columnWidth=29;header(comp,'I26:M26',['Python severity','Attained count','Pass count','Missed interest','Principal shortfall']);
[.6,.65,.7].forEach((v,i)=>{const r=27+i,rs=(an.stress_results||[]).filter(x=>Math.abs(x.senior_pct-c.base_senior_pct)<1e-9&&Math.abs(x.target_default_rate-v)<1e-9),nonempty=rs.length>0;
 values(comp,`I${r}`,[[v,nonempty?rs.filter(x=>x.default_target_attained).length:null,nonempty?rs.filter(x=>x.default_target_attained&&x.accounting_valid&&x.senior_pass).length:null,nonempty?Math.max(...rs.map(x=>x.senior_timely_interest_shortfall)):null,nonempty?Math.max(...rs.map(x=>x.senior_principal_shortfall)):null]]);
 values(comp,`C${r}`,[[v]]);for(let j=0;j<4;j++)formula(comp,`${col(4+j)}${r}`,nonempty?gated(`${col(10+j)}${r}`):'="NOT RUN"');
});
comp.getRange('C27:C29').setNumberFormat(F.pct);comp.getRange('F27:G29').setNumberFormat(F.amount);comp.getRange('I27:I29').setNumberFormat(F.pct);comp.getRange('L27:M29').setNumberFormat(F.amount);source(comp,'I27:M29');
values(comp,'C31',[['60%, 65% and 70% are sensitivity points, with no assigned rating or probability.'],['The same existing stress matrix is tested at each point; no agency hurdle has been assumed.'],['Next: resolve missing inputs on Gaps and Sources, then review all Checks.']]);comp.freezePanes.freezeRows(7);

const gaps=s['Gaps and Sources'];title(gaps,'What Is Still Needed','Resolve data gaps and implementation work separately. Full instructions are in docs/OUTSTANDING_AND_NEXT_STEPS.md.','G');
gaps.getRange('C:C').format.columnWidth=29;gaps.getRange('D:D').format.columnWidth=44;gaps.getRange('E:E').format.columnWidth=67;gaps.getRange('F:F').format.columnWidth=62;gaps.getRange('G:G').format.columnWidth=72;
header(gaps,'C7:G7',['Item / owner','Current treatment','What to provide or implement','Assumptions allowed now','Where it comes from']);
const gapRows=[
 ['S&P WARF / implemented','Sourced factors and live formulas','Review rating assignment / eligibility for the actual deal. No missing factor table remains for the supported scope.','The fictional ratings are retained and labelled. No ordinal or Fitch factor substitution.','SP Credit Parameters; Blue Owl original November 2025 filing; S&P AUF Table 13'],
 ['S&P AAA SDR / credit model','Unavailable unless externally supplied','Check FT access to CDO Evaluator via Ratings360. Import portfolio-specific output with source/version, date, criteria and input hashes; alternatively build and benchmark a criteria-informed engine.','Keep formal SDR blank. Use labelled development default sensitivities for exploration.','S&P CDO Suite of Models; core criteria default, correlation and quantile tables'],
 ['S&P Monitor / implementation','Not implemented','Confirm eligibility, exact asset codes, regions, maturity definitions and transaction-specific BDR coefficients.','Do not borrow another deal\'s coefficients or treat an unverified regression as agency SDR.','S&P CDO Monitor technical articles and applicable transaction documents'],
 ['Fitch ratings / input owner','Separate sidecar; example is development_proxy','Supply public Fitch IDRs or reviewed Appendix 5 equivalencies with source evidence for every obligor.','Same-symbol fictional proxies are explicit, optional example inputs only.','Fitch Inputs; Appendix 5; templates/fitch_inputs_dictionary.csv'],
 ['Fitch recovery / input owner','Whole WARR gated on complete coverage','Resolve seven example facilities without a reviewed recovery classification. Check issue recovery opinions before fallback rules.','Example first-lien fallbacks are sourced but expressly assumed. No zero for missing recovery.','Fitch Appendix 4 and Appendix 6; docs/fitch_inputs.md'],
 ['Industry taxonomy / input owner','S&P supplied labels; Fitch blank','Map agency-specific classifications and retain review evidence. Supplied text similarity is insufficient.','No automatic cross-agency industry mapping.','S&P asset codes; Fitch PCM industry classification'],
 ['Fitch RDR/RLR / credit model','Not calculated','Obtain / run the applicable Fitch Portfolio Credit Model and retain complete inputs, assumptions and version.','No assumed AAA percentile or hurdle imported from S&P.','Fitch PCM; criteria default/loss distributions and Appendix 6'],
 ['Actual deal terms / deal owner','Fictional editable development terms','Provide term sheet / waterfall, payment dates, coupons, fees, OC/IC definitions, collateral haircuts, reinvestment conditions and legal final maturity.','64/26/10 is user-specified; all other development terms stay labelled until replaced.','Assumptions provenance; deal documents'],
 ['Cash-flow engine / engineering','Independent simplified waterfall','Implement agency-specific collateral amortisation, default / recovery timing, full rate and prepayment scenarios, event tests and required payment promises.','Development scenarios can test behaviour; they are not agency BDRs.','S&P framework; Fitch criteria pages 18–23; docs/cashflow_design.md'],
 ['Schedules and asset detail / data','18 supplied fields','Add next coupon/reset date, day-count, amortisation, accrued interest and reviewed recovery hierarchy as scope requires.','Bullet maturity and synthetic coupon anchor are disclosed development conventions.','Servicer / trustee / loan records'],
 ['Benchmarking / validation','Fictional implementation tests','Compare representative results against trusted agency / approved internal outputs, then validate full Excel recalculation in the FT runtime.','Passing software tests is not rating-model calibration.','docs/validation_report.md; FT approved local environment'],
 ['New LLM / maintainer','Documented handover','Start with LLM_HANDOVER.md, then README, dictionaries, methodology and tests; preserve output/status boundaries.','No real data uploads. No promotion of proxies to agency conclusions.','docs/LLM_HANDOVER.md']
];values(gaps,'C8',gapRows);gaps.getRange(`C8:G${7+gapRows.length}`).format.wrapText=true;gaps.getRange(`8:${7+gapRows.length}`).format.rowHeight=86;gaps.freezePanes.freezeRows(7);

// Explicit colour and text categories make agency ownership easy to follow.
const categories={
 'Read Me':['Guide','#203955'],'Agency Comparison':['Combined output','#167D8D'],'Outputs':['Development output','#167D8D'],
 'Portfolio Inputs':['Shared source','#81909E'],'Assumptions':['Shared deal inputs','#D6A43A'],'Portfolio Calc':['Shared portfolio / S&P factors','#81909E'],'Obligor Calc':['Shared grouping','#81909E'],'Capital Calc':['Shared capital structure','#81909E'],
 'SP Credit Parameters':['S&P sources','#3075B9'],'Concentration Calc':['S&P supplemental arithmetic','#3075B9'],
 'Fitch Inputs':['Fitch source / assumptions','#8859A3'],'Fitch Parameters':['Fitch sources','#8859A3'],'Fitch Calc':['Fitch calculations','#8859A3'],
 'Stress Inputs':['Development / S&P-informed timing','#D88238'],'Cash Flow Calc':['Development cash flow','#D88238'],'Sensitivity':['Development sizing tests','#D88238'],'Stress Results':['Development simulations','#D88238'],
 'Checks':['Validation','#BE5555'],'Gaps and Sources':['Guide / outstanding work','#203955'],'Methodology':['Guide / source register','#203955'],'Run Snapshot':['Shared run baseline','#81909E']
};
for(const [name,[label,colour]] of Object.entries(categories)){const sh=s[name];sh.tabColor=colour;const cell=['Portfolio Inputs','Obligor Calc','Stress Inputs','Stress Results','Run Snapshot','Fitch Inputs'].includes(name)?'A1':'C1';values(sh,cell,[[label]]);sh.getRange(cell).format.font={name:'Arial',size:10,bold:true,color:colour};}
values(out,'C37',[['See Agency Comparison for the separate S&P and Fitch metrics and missing prerequisites.']]);
// Presentation refinements from whole-workbook visual review.
fi.getRange('G:G').format.columnWidth=34;fi.getRange('H:H').format.columnWidth=98;fi.getRange(`8:${fe}`).format.rowHeight=107;fi.getRange(`A8:X${fe}`).format.verticalAlignment='top';
sp.getRange('C29').format.wrapText=true;sp.getRange('29:29').format.rowHeight=40;
values(fc,'F7',[['WARF calculation basis']]);values(fc,'F9',[['WARR calculation status']]);
for(const row of [9,11,13])fc.getRange(`D${row}`).setNumberFormat('0.0%');comp.getRange('D12:E12').setNumberFormat('0.0%');
pc.getRange('D21:D21').setNumberFormat('#,##0.00');comp.getRange('D9').setNumberFormat('#,##0.00');comp.getRange('E9').setNumberFormat('0.000');
comp.getRange('D8:E23').format.horizontalAlignment='center';
for(const letter of ['C','D','E'])comp.getRange(`${letter}8:${letter}17`).format.borders={right:{style:'thin',color:C.line}};
ck.getRange(`E8:E${refreshRow+1}`).format.borders={right:{style:'thin',color:C.line}};
ash.getRange('C:C').format.columnWidth=52;ash.getRange(`C8:C${ar-1}`).format.wrapText=true;ash.getRange(`8:${ar-1}`).format.rowHeight=40;ash.getRange('D38:E38').format.wrapText=true;ash.getRange('38:38').format.rowHeight=86;
for(let i=0;i<assumptionRows.length;i++)if(typeof assumptionRows[i].value==='boolean')values(ash,`F${8+i}`,[['flag']]);

// Every sheet has a readable font, source units and only bounded formula ranges.
for(const sh of Object.values(s)){sh.getUsedRange().format.font.name='Arial';}
ob.getRange(`F8:H${7+obs.length}`).format.font.color=C.green;
ob.getRange(`I8:I${7+obs.length}`).format.font.color='#000000';
cf.getRange(`E63:${lastCF}72`).format.font.color='#000000';
cf.getRange(`E69:${lastCF}70`).format.font.color=C.green;
ck.getRange(`D8:D${kr-1}`).format.font.color=C.green;
const qaChecks=[];
if(!packet.template){
 const baseline=ash.getRange('D12').values[0][0];
 ash.getRange('D12').values=[[baseline===.65?.64:.65]];
 const changed=out.getRange('D24').values[0][0];
 if(changed!=='REFRESH REQUIRED')throw new Error(`Assumption refresh detection failed: ${changed}`);
 qaChecks.push({test:'Edited senior assumption triggers refresh',passed:true});
 ash.getRange('D12').values=[[baseline]];
 const curveBase=stress.getRange('E8').values[0][0];stress.getRange('E8').values=[[curveBase+.001]];
 if(out.getRange('D24').values[0][0]!=='REFRESH REQUIRED')throw new Error('Stress rate refresh detection failed');
 qaChecks.push({test:'Edited rate path triggers refresh',passed:true});stress.getRange('E8').values=[[curveBase]];
 const parBase=pin.getRange('D8').values[0][0];pin.getRange('D8').values=[[parBase+100]];
 if(out.getRange('D24').values[0][0]!=='REFRESH REQUIRED')throw new Error('Portfolio edit refresh detection failed');
 if(Math.abs(pc.getRange('D8').values[0][0]-(a.total_par+100))>.01)throw new Error('Live portfolio formula failed to recalculate');
 qaChecks.push({test:'Edited portfolio triggers refresh and recalculates total',passed:true});pin.getRange('D8').values=[[parBase]];
 const fitchBase=fi.getRange('C8').values[0][0];fi.getRange('C8').values=[[fitchBase==='B'?'BB':'B']];
 if(comp.getRange('E9').values[0][0]!=='REFRESH REQUIRED')throw new Error('Fitch source refresh detection failed');
 qaChecks.push({test:'Edited Fitch source suppresses comparison results',passed:true});fi.getRange('C8').values=[[fitchBase]];
 const spFactor=sp.getRange('D8').values[0][0];sp.getRange('D8').values=[[spFactor+1]];
 if(comp.getRange('D9').values[0][0]!=='REFRESH REQUIRED')throw new Error('S&P parameter edit detection failed');
 qaChecks.push({test:'Edited source parameter triggers refresh',passed:true});sp.getRange('D8').values=[[spFactor]];
 if(Math.abs(pc.getRange('D21').values[0][0]-cq.spwarf)>1e-6)throw new Error('SPWARF Excel/Python disagreement');
 if(Math.abs(pc.getRange('D23').values[0][0]-cq.default_rate_dispersion)>1e-6)throw new Error('S&P dispersion Excel/Python disagreement');
 if(fp.warf!==null&&Math.abs(fc.getRange('D10').values[0][0]-fp.warf)>1e-6)throw new Error('Fitch WARF Excel/Python disagreement');
 if(fp.warr===null&&typeof fc.getRange('D12').values[0][0]==='number')throw new Error('Missing recovery inputs must suppress Fitch WARR');
 qaChecks.push({test:'Agency metrics reconcile and incomplete WARR is gated',passed:true});
 if(ck.getRange(`D${refreshRow}`).values[0][0]!==false)throw new Error('Refresh flag did not reset: '+JSON.stringify({checks:ck.getRange('C8:D17').values,fitch:fc.getRange('C17:D18').values,sp:sp.getRange('D29').values}));
}
const inspect=await w.inspect({kind:'table',range:'Outputs!C7:D29',include:'values,formulas',tableMaxRows:24,tableMaxCols:2,maxChars:7000});
const errors=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Final formula error scan',maxChars:5000});
if(/#REF!|#DIV\/0!|#VALUE!|#NAME\?|#N\/A|#NUM!|#NULL!|#SPILL!|#CALC!/.test(errors.ndjson))throw new Error(`Workbook formula error scan failed: ${errors.ndjson}`);
console.log(JSON.stringify({run:packet.run_id,inspection:inspect.ndjson,formulaErrors:errors.ndjson}));
const qaAt=extra.indexOf('--qa');
if(qaAt>=0){
 const qa=extra[qaAt+1];await fs.mkdir(qa,{recursive:true});
 await fs.writeFile(path.join(qa,'inspection.json'),JSON.stringify({inspect:inspect.ndjson,errors:errors.ndjson,qaChecks},null,2));
 const ranges={'Read Me':'C1:E19','Agency Comparison':'C1:G33','SP Credit Parameters':'C1:F29','Fitch Inputs':'A1:H13','Fitch Parameters':'C1:G32','Fitch Calc':'C1:F19','Gaps and Sources':'C1:F19','Outputs':'C1:H37','Portfolio Inputs':'A1:H16','Assumptions':'C1:H18','Stress Inputs':'A1:I16','Portfolio Calc':'C1:I23','Obligor Calc':'A1:I16','Capital Calc':'C1:J19','Concentration Calc':'C1:K15','Cash Flow Calc':'C1:J24','Sensitivity':'C1:I18','Stress Results':'A1:H16','Checks':'C1:H21','Methodology':'C1:F19','Run Snapshot':'A1:H16'};
 for(const [name,range]of Object.entries(ranges)){
  try{const blob=await w.render({sheetName:name,range,scale:1.3,format:'png'});await fs.writeFile(path.join(qa,name.replaceAll(' ','_')+'.png'),new Uint8Array(await blob.arrayBuffer()));}
  catch(e){throw new Error(`Visual render failed for ${name}: ${e.message}`);}
 }
 for(const [file,sheetName,range]of [['Portfolio_chart','Portfolio Calc','K7:S27'],['Cash_flow_checks','Cash Flow Calc','C61:J72'],['Sensitivity_boundaries','Sensitivity','P7:S18']]){const blob=await w.render({sheetName,range,scale:1.3,format:'png'});await fs.writeFile(path.join(qa,file+'.png'),new Uint8Array(await blob.arrayBuffer()));}
 const panels=[['Read_Me_more','Read Me',`C20:E${7+readRows.length}`],['Fitch_input_formulas','Fitch Inputs','I7:X12'],['Portfolio_input_credit','Portfolio Inputs','I7:AB14'],['Cash_flow_middle','Cash Flow Calc','C25:J44'],['Cash_flow_debt','Cash Flow Calc','C45:J60'],['Cash_flow_final','Cash Flow Calc',`${col(Math.max(5,periods.length))}7:${lastCF}72`],['Checks_more','Checks',`C22:H${refreshRow+1}`],['Stress_results_more','Stress Results','I7:S16'],['Methodology_sources','Methodology','G7:G19'],['Gap_sources','Gaps and Sources','G7:G19']];
 for(let r=19;r<ar;r+=15)panels.push([`Assumptions_${r}`,'Assumptions',`C${r}:H${Math.min(ar-1,r+14)}`]);
 for(const [file,sheetName,range]of panels){const blob=await w.render({sheetName,range,scale:1.1,format:'png'});await fs.writeFile(path.join(qa,file+'.png'),new Uint8Array(await blob.arrayBuffer()));}
}
await fs.mkdir(path.dirname(output),{recursive:true});const xlsx=await SpreadsheetFile.exportXlsx(w);await xlsx.save(output);
console.log(`Saved workbook: ${path.basename(output)}`);

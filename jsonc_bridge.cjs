const fs=require('fs');
const {parse, modify, applyEdits}=require('jsonc-parser');
const [, , op, file, pathJson, value, type]=process.argv;
const text=fs.readFileSync(file,'utf8'); const doc=parse(text);
function flatten(x,p=[]){let out=[]; if(x&&typeof x==='object'&&!Array.isArray(x)) for(const [k,v] of Object.entries(x)) out=out.concat(flatten(v,p.concat(k))); else {let t=Array.isArray(x)?'array':x===null?'null':typeof x; out.push({path:p,label:p.join('.'),value:Array.isArray(x)?JSON.stringify(x):String(x),value_type:t});} return out;}
if(op==='list'){process.stdout.write(JSON.stringify(flatten(doc))); process.exit();}
let parsed=value; if(type==='string') parsed=value; else if(type==='boolean') parsed=['true','1','yes','on'].includes(value.toLowerCase()); else if(type==='number') parsed=Number(value); else if(type==='array'||type==='object') parsed=JSON.parse(value); else if(type==='null') parsed=null;
const edits=modify(text,JSON.parse(pathJson),parsed,{formattingOptions:{insertSpaces:true,tabSize:2}}); process.stdout.write(applyEdits(text,edits));

const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync('fairycodex.html','utf8'),start=html.indexOf('const CATALOG='),end=html.indexOf('\n];',start)+3;
if(start<0||end<start)throw Error('Owned Fairy catalog not found');
const context={};vm.createContext(context);vm.runInContext(html.slice(start,end)+';globalThis.catalog=CATALOG;',context,{timeout:1000});
fs.writeFileSync('desktop/assets/fairy-catalog.json',JSON.stringify(context.catalog,null,2));
console.log(context.catalog.length+' shared treasure records generated');

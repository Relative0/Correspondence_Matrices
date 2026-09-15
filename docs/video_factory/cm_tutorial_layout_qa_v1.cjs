// Read-only DOM geometry checks of authored local teaching diagrams.
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../..');
const {chromium}=require(path.join(root,'../PoP/Tools/POP-Video-Creator/node_modules/playwright'));
const out=path.join(__dirname,'deep_series/foundational_cm_tutorial_series_v1');
(async()=>{
 const lessons=JSON.parse(fs.readFileSync(path.join(out,'CURRICULUM_V1.json'),'utf8'));
 const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:720}});const checks=[];
 for(const l of lessons)for(let i=0;i<l.scenes.length;i++){
  const file=path.join(out,l.id,'visuals',`${String(i+1).padStart(2,'0')}.html`);
  await page.setContent(fs.readFileSync(file,'utf8'));await page.evaluate(()=>document.fonts.ready);
  const result=await page.evaluate(()=>{
   const main=document.querySelector('main').getBoundingClientRect();const note=document.querySelector('.takeaway').getBoundingClientRect();
   const errors=[];
   for(const el of document.querySelectorAll('main td,main th,main .equation,main .trace-line,main .tag,main .small')){
    const r=el.getBoundingClientRect();
    if(r.left<35||r.right>1245||r.top<main.top-1||r.bottom>note.top-8)errors.push({text:el.textContent.slice(0,100),bounds:{left:r.left,right:r.right,top:r.top,bottom:r.bottom},reason:'outside teaching region'});
    if(el.scrollWidth>el.clientWidth+2)errors.push({text:el.textContent.slice(0,100),reason:'horizontal overflow'});
   }
   if(note.scrollHeight>note.clientHeight+2)errors.push({reason:'takeaway overflow'});
   return {errors,mainTop:main.top,noteTop:note.top};
  });checks.push({lesson:l.id,scene:i+1,...result});
 }
 await browser.close();const errors=checks.filter(x=>x.errors.length);
 fs.writeFileSync(path.join(out,'LAYOUT_QA_V1.json'),JSON.stringify({frames:checks.length,failed_frames:errors.length,checks},null,2));
 console.log(JSON.stringify({frames:checks.length,failed:errors},null,2));if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../..');
const {chromium}=require(path.join(root,'../PoP/Tools/POP-Video-Creator/node_modules/playwright'));
const out=path.join(__dirname,'deep_series/foundational_cm_tutorial_series_v2');
(async()=>{
 const lessons=JSON.parse(fs.readFileSync(path.join(out,'CURRICULUM_V2.json'),'utf8'));
 const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:720}});const checks=[];
 for(const l of lessons)for(let i=0;i<l.scenes.length;i++){
  const file=path.join(out,l.id,'visuals',`${String(i+1).padStart(2,'0')}.html`);
  await page.setContent(fs.readFileSync(file,'utf8'));await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>window.__seek(0));
  const result=await page.evaluate(()=>{
   const main=document.querySelector('main').getBoundingClientRect(),note=document.querySelector('.takeaway').getBoundingClientRect(),errors=[];
   for(const el of document.querySelectorAll('main td,main th,main .equation,main .trace-line,main .tag,main .small,main .calculation,main .calc-chain')){
    const r=el.getBoundingClientRect();
    if(r.left<35||r.right>1245||r.top<main.top-1||r.bottom>note.top-8)errors.push({text:el.textContent.slice(0,100),bounds:{left:r.left,right:r.right,top:r.top,bottom:r.bottom},reason:'outside teaching region'});
    if(el.scrollWidth>el.clientWidth+2)errors.push({text:el.textContent.slice(0,100),reason:'horizontal overflow'});
   }
   for(const svg of document.querySelectorAll('.impax')){
    const [h,v]=[...svg.querySelectorAll('text')].map(e=>e.getBoundingClientRect());
    const dx=Math.abs(h.left+h.width/2-v.left-v.width/2),dy=Math.abs(h.top+h.height/2-v.top-v.height/2);
    if(dx>.5||dy>.5)errors.push({reason:'Impax glyph centers differ',dx,dy});
   }
   return {errors,mainTop:main.top,noteTop:note.top};
  });checks.push({lesson:l.id,scene:i+1,...result});
 }
 await browser.close();const failed=checks.filter(x=>x.errors.length);
 fs.writeFileSync(path.join(out,'LAYOUT_QA_V2.json'),JSON.stringify({frames:checks.length,failed_frames:failed.length,checks},null,2));
 console.log(JSON.stringify({frames:checks.length,failed},null,2));if(failed.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

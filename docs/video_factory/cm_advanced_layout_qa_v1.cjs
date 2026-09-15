const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../..');
const {chromium}=require(path.join(root,'../PoP/Tools/POP-Video-Creator/node_modules/playwright'));
const out=path.join(__dirname,'deep_series/advanced_cm_tutorial_series_v1');
(async()=>{
 const lessons=JSON.parse(fs.readFileSync(path.join(out,'CURRICULUM_V1.json'),'utf8'));
 const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:720}});const checks=[];
 for(const l of lessons)for(let i=0;i<l.scenes.length;i++){
  const file=path.join(out,l.id,'visuals',`${String(i+1).padStart(2,'0')}.html`);
  await page.setContent(fs.readFileSync(file,'utf8'));await page.evaluate(()=>document.fonts.ready);
  const result=await page.evaluate(()=>{
   const errors=[];const note=document.querySelector('.takeaway').getBoundingClientRect();
   for(const el of document.querySelectorAll('main td,main th,main .equation,main .line,main h3,header h1,.takeaway,.source')){
    const r=el.getBoundingClientRect(),isMain=Boolean(el.closest('main'));
    if(r.left<40||r.right>1240||r.top<0||r.bottom>719||(isMain&&r.bottom>note.top-8))errors.push({text:el.textContent.slice(0,90),bounds:{left:r.left,right:r.right,top:r.top,bottom:r.bottom},reason:'outside safe region'});
    if(el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2)errors.push({text:el.textContent.slice(0,90),reason:'overflow'});
   }
   if(/[→⊕]/.test(document.querySelector('main').textContent))errors.push({reason:'forbidden mathematical arrow or XOR glyph'});
   return {errors};
  });checks.push({lesson:l.id,scene:i+1,...result});
 }
 await browser.close();const failed=checks.filter(x=>x.errors.length);
 fs.writeFileSync(path.join(out,'LAYOUT_QA_V1.json'),JSON.stringify({frames:checks.length,failed_frames:failed.length,checks},null,2));
 console.log(JSON.stringify({frames:checks.length,failed},null,2));if(failed.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});

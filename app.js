const $=s=>document.querySelector(s);
let me=null, view="news";
async function api(url,opts={}){const r=await fetch(url,{...opts,headers:{"Content-Type":"application/json",...(opts.headers||{})}});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.detail||"Произошла ошибка");return d}
function formData(form){return Object.fromEntries(new FormData(form).entries())}
function msg(t){$("#authMsg").textContent=t}
document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>{document.querySelectorAll("[data-tab]").forEach(x=>x.classList.toggle("active",x===b));$("#loginForm").hidden=b.dataset.tab!=="login";$("#registerForm").hidden=b.dataset.tab!=="register";msg("")});
$("#loginForm").onsubmit=async e=>{e.preventDefault();try{await api("/api/login",{method:"POST",body:JSON.stringify(formData(e.target))});await start()}catch(x){msg(x.message)}};
$("#registerForm").onsubmit=async e=>{e.preventDefault();try{await api("/api/register",{method:"POST",body:JSON.stringify(formData(e.target))});await start()}catch(x){msg(x.message)}};
$("#logout").onclick=async()=>{await api("/api/logout",{method:"POST"});me=null;$("#app").hidden=true;$("#auth").hidden=false;$("#who").textContent=""};
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>show(b.dataset.view));
async function start(){try{me=await api("/api/me");$("#auth").hidden=true;$("#app").hidden=false;$("#who").textContent=me.display_name+" · "+(me.role==="admin"?"администратор":"участник");$("#adminTools").hidden=me.role!=="admin";await show("news")}catch{ $("#auth").hidden=false;$("#app").hidden=true}}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function card(title,body,meta="",extra=""){return `<article class="item"><h3>${esc(title)}</h3><div>${esc(body).replace(/\n/g,"<br>")}</div>${extra}<div class="meta">${esc(meta)}</div></article>`}
async function show(v){view=v;document.querySelectorAll("[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===v));const c=$("#content");c.innerHTML="<p class='muted'>Загрузка…</p>";try{
if(v==="news"){let a=await api("/api/news");c.innerHTML="<h2>Новости</h2>"+(a.length?a.map(x=>card(x.title,x.body,x.author+" · "+new Date(x.created_at).toLocaleString())).join(""):"<p class='empty'>Новостей пока нет.</p>")}
if(v==="tasks"){let a=await api("/api/tasks");c.innerHTML="<h2>Задания</h2>"+(a.length?a.map(x=>card(x.title,x.description,"Срок: "+(x.due_date||"не указан"),!x.done?`<button class="primary" onclick="doneTask(${x.id})">Отметить выполненным</button>`:"<span class='meta'>Выполнено</span>")).join(""):"<p class='empty'>Заданий пока нет.</p>")}
if(v==="auction"){let a=await api("/api/auction");c.innerHTML="<h2>Аукцион</h2>"+(a.length?a.map(x=>card(x.title,x.description,"Текущая цена: "+x.current_bid,`<form onsubmit="bid(event,${x.id})"><input name="amount" type="number" min="${x.current_bid+1}" placeholder="Ваша ставка" required><button class="primary">Сделать ставку</button></form>`)).join(""):"<p class='empty'>Лотов пока нет.</p>")}
if(v==="duties"){let a=await api("/api/duties");c.innerHTML="<h2>Дежурства и отчёты</h2><form id='dutyForm'><input name='location' placeholder='Место дежурства' required><textarea name='note' placeholder='Комментарий'></textarea><button class='primary'>Отправить отчёт</button></form>"+(a.length?a.map(x=>card(x.location,x.note,x.author+" · "+new Date(x.created_at).toLocaleString())).join(""):"<p class='empty'>Отчётов пока нет.</p>");$("#dutyForm").onsubmit=async e=>{e.preventDefault();try{await api("/api/duties",{method:"POST",body:JSON.stringify(formData(e.target))});show("duties")}catch(x){alert(x.message)}}}
}catch(e){c.innerHTML=`<p class="message">${esc(e.message)}</p>`}}
window.doneTask=async id=>{try{await api(`/api/tasks/${id}/done`,{method:"POST"});show("tasks")}catch(e){alert(e.message)}};
window.bid=async(e,id)=>{e.preventDefault();try{await api(`/api/auction/${id}/bid`,{method:"POST",body:JSON.stringify({amount:Number(new FormData(e.target).get("amount"))})});show("auction")}catch(x){alert(x.message)}};
async function adminForm(id,url){$(id).onsubmit=async e=>{e.preventDefault();try{await api(url,{method:"POST",body:JSON.stringify(formData(e.target))});e.target.reset();show(view);alert("Готово")}catch(x){alert(x.message)}}}
adminForm("#newsForm","/api/news");adminForm("#taskForm","/api/tasks");adminForm("#lotForm","/api/auction");
start();

(()=>{const t=s=>window.orangibleTranslate?window.orangibleTranslate(s):s;
 const grid=document.getElementById('fruit-grid');if(!grid)return;
 const more=document.getElementById('load-more-fruits'), hidden=document.getElementById('hidden-fruit-grid');
 if(more&&hidden){more.addEventListener('click',()=>{const open=more.getAttribute('aria-expanded')==='true';hidden.hidden=open;more.setAttribute('aria-expanded',String(!open));more.textContent=open?t('加载更多（')+hidden.children.length+'） ↓':t('收起商品 ↑');});}
 async function refresh(){if(document.hidden)return;try{
 const response=await fetch('/fruit-market/',{cache:'no-store'});if(!response.ok)return;
 const data=await response.json();if(grid.dataset.day!==data.day){location.reload();return;}
 const items=new Map(data.products.map(p=>[String(p.id),p]));const grids=[grid,...(hidden?[hidden]:[])];
 for(const list of grids){const cards=[...list.querySelectorAll('[data-product]')];for(const card of cards){const row=items.get(card.dataset.product);if(!row||row.dormant!==card.classList.contains('is-dormant')){location.reload();return;}card.querySelector('.live-sales').textContent=row.sales;card.querySelector('.live-price').textContent='¥'+row.price;const badge=card.querySelector('.discount');if(badge)badge.textContent='−'+row.discount+'%';}
 if(grid.dataset.sort==='sales')cards.sort((a,b)=>items.get(b.dataset.product).sales-items.get(a.dataset.product).sales||Number(a.dataset.product)-Number(b.dataset.product)).forEach(c=>list.append(c));
 if(grid.dataset.sort==='price')cards.sort((a,b)=>Number(items.get(a.dataset.product).price)-Number(items.get(b.dataset.product).price)).forEach(c=>list.append(c));}
 }catch(e){/* Keep the rendered catalog available if the request fails. */}}
 setInterval(refresh,5000);document.addEventListener('visibilitychange',refresh);
})();

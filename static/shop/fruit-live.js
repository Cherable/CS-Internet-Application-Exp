(() => {
 const grid=document.getElementById('fruit-grid'); if(!grid)return;
 async function refresh(){
  if(document.hidden)return;
  try{
   const response=await fetch('/fruit-market/',{cache:'no-store'}); if(!response.ok)return;
   const data=await response.json(); if(grid.dataset.day!==data.day){location.reload();return;} const items=new Map(data.products.map(p=>[String(p.id),p]));
   const cards=[...grid.querySelectorAll('[data-product]')];
   cards.forEach(card=>{const row=items.get(card.dataset.product);if(!row){card.remove();return;}card.querySelector('.live-sales').textContent=row.sales;card.querySelector('.live-price').textContent='¥'+row.price;const badge=card.querySelector('.discount');if(badge)badge.textContent='−'+row.discount+'%';});
   if(grid.dataset.sort==='sales'){cards.filter(c=>c.isConnected).sort((a,b)=>items.get(b.dataset.product).sales-items.get(a.dataset.product).sales||Number(a.dataset.product)-Number(b.dataset.product)).forEach(c=>grid.append(c));}
   if(grid.dataset.sort==='price'){cards.filter(c=>c.isConnected).sort((a,b)=>Number(items.get(a.dataset.product).price)-Number(items.get(b.dataset.product).price)).forEach(c=>grid.append(c));}
  }catch(e){/* The rendered catalog remains available during network interruptions. */}
 }
 setInterval(refresh,5000); document.addEventListener('visibilitychange',refresh);
})();

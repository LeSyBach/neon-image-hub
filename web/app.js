const $=id=>document.getElementById(id);
let query='',page=1,pages=1,requestVersion=0,activeJob=null,pollTimer=null;
const date=new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
async function api(path,options={}){
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});
  const data=await response.json();
  if(!response.ok){throw new Error(typeof data.detail==='string'?data.detail:'Yêu cầu chưa hợp lệ. Vui lòng kiểm tra tên tiếng Anh.');}
  return data;
}
function error(message){$('search-error').textContent=message;$('search-error').hidden=!message;}
function syncUrl(){const u=new URL(location);u.search='';if(query)u.searchParams.set('q',query);if(page>1)u.searchParams.set('page',page);if(activeJob)u.searchParams.set('job',activeJob);history.replaceState({},'',u);}
function openImage(image){
  $('large-image').src=image.url;$('large-image').alt=image.name;
  $('image-title').textContent=image.name;
  $('image-detail').textContent=`AI ${image.worker_id} · ${image.width} × ${image.height} px · ${date.format(image.created*1000)}`;
  $('download-image').href=image.url;$('download-image').download=image.filename;
  $('image-dialog').showModal();
}
async function gallery(version=requestVersion){
  const data=await api(`/api/images?page=${page}&q=${encodeURIComponent(query)}`);
  if(version!==requestVersion)return;
  pages=data.pages;
  if(page>pages){page=pages;syncUrl();return gallery(version);}
  const fragment=document.createDocumentFragment();
  for(const image of data.items){
    const card=$('image-card').content.cloneNode(true);
    const img=card.querySelector('img');img.src=image.url;img.alt=image.name;img.width=image.width;img.height=image.height;
    card.querySelector('strong').textContent=image.name;
    card.querySelector('.image-caption>span').textContent=`AI ${image.worker_id} · ${image.width} × ${image.height}`;
    card.querySelector('button').setAttribute('aria-label',`Xem ảnh ${image.name}`);
    card.querySelector('button').addEventListener('click',()=>openImage(image));fragment.append(card);
  }
  $('gallery').replaceChildren(fragment);$('gallery').setAttribute('aria-busy','false');
  $('collection-title').textContent=query?`Ảnh về “${query}”`:'Ảnh mới nhất';
  $('collection-count').textContent=`${data.total} ảnh${data.total?' · Mới nhất trước':''}`;
  $('show-all').hidden=!query;$('empty').hidden=data.items.length>0;
  $('empty-title').textContent=query?'Yêu cầu của bạn đang được xử lý':'Kho ảnh đang chờ những hình đầu tiên';
  $('empty-text').textContent=query?'Ảnh sẽ tự xuất hiện tại đây khi hoàn thành.':'Tìm một nội dung bằng tiếng Anh để bắt đầu.';
  $('pagination').hidden=pages<=1;$('previous').disabled=page<=1;$('next').disabled=page>=pages;
  $('page-number').textContent=`Trang ${page} / ${pages}`;
}
async function stats(){
  try{const data=await api('/api/stats');$('total-images').textContent=data.total_images;
    const fragment=document.createDocumentFragment();
    for(const ai of data.workers){const li=document.createElement('li');li.append(`AI ${ai.id}`);const n=document.createElement('strong');n.textContent=`${ai.images} ảnh`;li.append(n);fragment.append(li);}
    $('ai-counts').replaceChildren(fragment);
  }catch{ /* A gallery request reports network failures; retain last known totals. */ }
}
async function poll(jobId,version){
  if(version!==requestVersion||jobId!==activeJob)return;
  try{
    const job=await api(`/api/jobs/${jobId}`);
    if(version!==requestVersion)return;
    $('retry').hidden=true;
    if(job.state==='succeeded'){
      $('generation-title').textContent='Ảnh đã sẵn sàng';$('generation-text').textContent=`“${job.name}” đã được lưu vào kho.`;
      activeJob=null;syncUrl();await gallery(version);await stats();return;
    }
    if(job.state==='failed'||job.state==='cancelled'){
      $('generation-title').textContent='Chưa thể hoàn thành ảnh';$('generation-text').textContent='Bạn có thể thử tạo lại. Yêu cầu cũ vẫn được lưu để kiểm tra.';
      $('retry').hidden=false;return;
    }
    $('generation-title').textContent=job.state==='running'?`Đang tạo “${job.name}”`:`Đang chuẩn bị “${job.name}”`;
    $('generation-text').textContent=job.state==='running'?'Bạn có thể giữ trang này mở; ảnh sẽ tự xuất hiện khi xong.':
      (job.available_workers?'Yêu cầu đã vào hàng chờ. Ảnh sẽ được tạo khi có máy sẵn sàng.':'Yêu cầu đã được lưu. Đang chờ máy sinh ảnh kết nối.');
  }catch(e){$('generation-text').textContent='Kết nối đang gián đoạn. Trang sẽ tự kiểm tra lại.';}
  pollTimer=setTimeout(()=>poll(jobId,version),3000);
}
async function search(name){
  name=name.trim().replace(/\s+/g,' ').toLowerCase();
  if(!name)return showAll();
  const version=++requestVersion;clearTimeout(pollTimer);activeJob=null;query=name;page=1;error('');
  $('search-input').value=name;$('search-button').disabled=true;$('generation').hidden=true;
  try{
    const result=await api('/api/search',{method:'POST',body:JSON.stringify({name})});
    if(version!==requestVersion)return;
    await gallery(version);await stats();
    if(result.state==='pending'){activeJob=result.job.id;$('generation').hidden=false;syncUrl();await poll(activeJob,version);}else{syncUrl();}
  }catch(e){if(version===requestVersion)error(e.message);}
  finally{if(version===requestVersion)$('search-button').disabled=false;}
}
async function showAll(){++requestVersion;clearTimeout(pollTimer);activeJob=null;query='';page=1;syncUrl();$('search-input').value='';$('generation').hidden=true;error('');try{await gallery();await stats();}catch{error('Chưa kết nối được kho ảnh. Vui lòng thử lại.');}}
$('search-form').addEventListener('submit',e=>{e.preventDefault();search($('search-input').value);});
document.querySelectorAll('[data-search]').forEach(b=>b.addEventListener('click',()=>search(b.dataset.search)));
$('show-all').addEventListener('click',showAll);$('retry').addEventListener('click',()=>search(query));
for(const [id,step] of [['previous',-1],['next',1]])$(id).addEventListener('click',async()=>{page+=step;syncUrl();try{await gallery();$('collection-title').scrollIntoView({block:'start'});}catch{error('Chưa tải được trang ảnh. Vui lòng thử lại.');}});
$('close-dialog').addEventListener('click',()=>$('image-dialog').close());
$('image-dialog').addEventListener('click',e=>{if(e.target===$('image-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
(async()=>{const url=new URL(location);query=url.searchParams.get('q')||'';page=Math.max(1,Number(url.searchParams.get('page'))||1);activeJob=url.searchParams.get('job');$('search-input').value=query;
try{await gallery();await stats();if(activeJob){$('generation').hidden=false;poll(activeJob,requestVersion);}else if(query){search(query);}}catch{error('Chưa kết nối được kho ảnh. Vui lòng thử lại.');}
setInterval(()=>{stats();if(!query&&page===1&&!document.hidden)gallery().catch(()=>{});},15000);
})();

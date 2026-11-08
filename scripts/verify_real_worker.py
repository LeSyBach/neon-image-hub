"""Browser verification against real server + local inference, not fixtures."""
import json
from pathlib import Path
import sys
import time

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'.tools/python'))
from playwright.sync_api import sync_playwright,expect

name=sys.argv[1] if len(sys.argv)>1 else 'black dog'
slug=name.replace(' ','-')
expected_worker=sys.argv[2] if len(sys.argv)>2 else '2.1'
expected_model=sys.argv[3] if len(sys.argv)>3 else 'sd-turbo'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8080',wait_until='networkidle')
    page.locator('#search-input').fill(name)
    start=time.monotonic()
    page.get_by_role('button',name='Tìm ảnh',exact=True).click()
    expect(page.locator('.image-card')).to_have_count(1,timeout=240000)
    expect(page.locator('.image-card img')).to_be_visible()
    elapsed=round(time.monotonic()-start,2)
    result=page.request.get('http://127.0.0.1:8080/api/images',params={'q':name}).json()
    image=result['items'][0]
    assert image['worker_id']==expected_worker and image['model_id']==expected_model
    assert image['width']>=128 and image['height']>=128
    raw=page.request.get('http://127.0.0.1:8080'+image['url'])
    assert raw.ok
    (root/f'test-results/{slug}-real.png').write_bytes(raw.body())
    before=page.request.get('http://127.0.0.1:8080/api/stats').json()
    response=page.request.post('http://127.0.0.1:8080/api/search',data={'name':name.upper()})
    assert response.status==200
    assert response.json()['image']['id']==image['id']
    page.locator('.image-open').click()
    expect(page.locator('#image-dialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#image-dialog')).not_to_be_visible()
    page.screenshot(path=str(root/'test-results/real-worker-desktop.png'),full_page=True)
    page.set_viewport_size({'width':375,'height':812})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(root/'test-results/real-worker-mobile.png'),full_page=True)
    assert not errors,errors
    report={'query':name,'worker_id':expected_worker,'model_id':image['model_id'],'image_id':image['id'],
            'filename':image['filename'],'browser_wait_seconds':elapsed,
            'same_session_image_visible':True,'repeat_search_reused_image':True,
            'dialog_and_escape':True,'mobile_no_horizontal_overflow':True,'javascript_errors':errors,
            'runtime':'one real CPU worker container + server on the same WSL host; not three physical workers'}
    (root/f'test-results/worker-e2e-{slug}.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
    browser.close()

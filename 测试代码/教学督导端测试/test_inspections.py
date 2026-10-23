"""教学督导检查意见：接口集成、持久化、权限、非法输入、异常场景。"""
from contextlib import closing
from 功能代码及实际项目文件.公共基础模块.db import connect

ROOT='/api/v1/supervisors/me/offerings'
HEAD={'X-Demo-User':'V001'}
GOOD={'category':'常规检查','conclusion':'正常','content':'课堂教学运行平稳，课程进度符合教学计划。'}


def offering_id(client):
    return client.get(ROOT,headers=HEAD).json()['data']['items'][0]['offering_id']


def endpoint(client):
    return f'{ROOT}/{offering_id(client)}/inspections'


def test_create_and_read_persistent(client):
    url=endpoint(client)
    assert client.get(url,headers=HEAD).json()['data']==[]
    response=client.post(url,headers=HEAD,json=GOOD)
    assert response.status_code==201
    saved=response.json()['data']
    assert saved['supervisor_id']=='V001' and saved['content']==GOOD['content']
    assert saved['created_at']
    assert client.get(url,headers=HEAD).json()['data'][0]['id']==saved['id']
    with closing(connect(client.app.state.db_path)) as db:
        assert db.execute('SELECT COUNT(*) FROM supervisor_inspections').fetchone()[0]==1


def test_append_history_and_order(client):
    url=endpoint(client)
    for note in ('第一次检查进展正常。','第二次检查情况正常。'):
        assert client.post(url,headers=HEAD,json={**GOOD,'content':note}).status_code==201
    history=client.get(url,headers=HEAD).json()['data']
    assert [x['content'] for x in history]==['第二次检查情况正常。','第一次检查进展正常。']


def test_isolation_across_offerings(client):
    items=client.get(ROOT,headers=HEAD).json()['data']['items']
    a,b=(x['offering_id'] for x in items[:2])
    client.post(f'{ROOT}/{a}/inspections',headers=HEAD,json=GOOD)
    assert client.get(f'{ROOT}/{b}/inspections',headers=HEAD).json()['data']==[]


def test_missing_offering_read_and_write(client):
    url=f'{ROOT}/99999/inspections'
    for response in (client.get(url,headers=HEAD),client.post(url,headers=HEAD,json=GOOD)):
        assert response.status_code==404 and response.json()['code']=='OFFERING_NOT_FOUND'


def test_auth_required(client):
    url=endpoint(client)
    assert client.get(url).status_code==401
    assert client.post(url,json=GOOD).status_code==401


def test_wrong_roles_cannot_read_or_write(client):
    url=endpoint(client)
    for user in ('S2024001','T003','D001'):
        for response in (client.get(url,headers={'X-Demo-User':user}),
                         client.post(url,headers={'X-Demo-User':user},json=GOOD)):
            assert response.status_code==403 and response.json()['code']=='ROLE_FORBIDDEN'


def test_unknown_identity(client):
    assert client.post(endpoint(client),headers={'X-Demo-User':'BOGUS'},json=GOOD).status_code==401


def test_empty_and_short_content_rejected(client):
    url=endpoint(client)
    for content in ('','abc','    ','  ab  '):
        result=client.post(url,headers=HEAD,json={**GOOD,'content':content})
        assert result.status_code==422
    assert client.get(url,headers=HEAD).json()['data']==[]


def test_long_content_rejected(client):
    response=client.post(endpoint(client),headers=HEAD,json={**GOOD,'content':'文'*1001})
    assert response.status_code==422


def test_invalid_category_and_conclusion(client):
    url=endpoint(client)
    for patch in ({'category':'随意类型'},{'conclusion':'已批准修改课表'}):
        response=client.post(url,headers=HEAD,json={**GOOD,**patch})
        assert response.status_code==422 and response.json()['code']=='PARAM_INVALID'


def test_missing_fields_and_bad_json(client):
    url=endpoint(client)
    assert client.post(url,headers=HEAD,json={'category':'常规检查'}).status_code==422
    assert client.post(url,headers={**HEAD,'Content-Type':'application/json'},content='{').status_code==422


def test_special_text_stored_as_data(client):
    note='<script>alert(1)</script>检查记录，不应该执行网页脚本。'
    result=client.post(endpoint(client),headers=HEAD,json={**GOOD,'content':note})
    assert result.status_code==201
    assert result.json()['data']['content']==note
    assert client.get(endpoint(client),headers=HEAD).json()['data'][0]['content']==note


def test_unexpected_offering_id_validation(client):
    for value in ('abc','0','-1'):
        result=client.post(f'{ROOT}/{value}/inspections',headers=HEAD,json=GOOD)
        assert result.status_code in (404,422)


def test_page_includes_inspection_controls(client):
    page=client.get('/supervisor').text
    assert 'inspection-form' in page and 'inspection-history' in page and '保存检查意见' in page


def test_no_course_mutation_after_inspection(client):
    before=client.get(ROOT,headers=HEAD).json()['data']
    client.post(endpoint(client),headers=HEAD,json=GOOD)
    after=client.get(ROOT,headers=HEAD).json()['data']
    assert before==after

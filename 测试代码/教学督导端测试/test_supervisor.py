"""新增US：教学督导查看课程开设情况，正常流程、边界、异常和权限回归。"""
from contextlib import closing
import pytest
from 功能代码及实际项目文件.公共基础模块.db import connect
from 功能代码及实际项目文件.教学督导端.service import list_offerings

BASE='/api/v1/supervisors/me/offerings'
HEAD={'X-Demo-User':'V001'}

def get(client, params=None, headers=HEAD):
    return client.get(BASE,params=params,headers=headers)

def test_page_and_portal(client):
    for route,text in [('/supervisor','教学督导中心'),('/portal','四端工作台')]:
        r=client.get(route)
        assert r.status_code==200 and text in r.text
    for route in ('/student','/teacher','/director'):
        assert client.get(route).status_code==200

def test_all_offerings_and_statistics(client):
    result=get(client)
    assert result.status_code==200
    data=result.json()['data']
    assert data['total']==4
    assert data['stats']=={'offerings':4,'courses':4,'published':3,'unpublished':1}
    assert {x['course_id'] for x in data['items']}=={'CS101','SE201','MA101','AI999'}
    assert data['page']==1 and data['total_pages']==1

def test_multiteacher_is_one_offering(client):
    items=get(client).json()['data']['items']
    math=[x for x in items if x['course_id']=='MA101']
    assert len(math)==1
    assert '张老师' in math[0]['teachers'] and '王老师' in math[0]['teachers']

def test_enrolled_count(client):
    by_id={x['course_id']:x for x in get(client).json()['data']['items']}
    assert by_id['SE201']['enrolled_count']==2
    assert by_id['CS101']['enrolled_count']==1

def test_keyword_course_name(client):
    data=get(client,{'keyword':'软件项目'}).json()['data']
    assert [x['course_id'] for x in data['items']]==['SE201']

def test_keyword_course_id(client):
    data=get(client,{'keyword':'MA101'}).json()['data']
    assert data['total']==1

def test_keyword_teaching_class(client):
    data=get(client,{'keyword':'联合2401'}).json()['data']
    assert data['total']==1 and data['items'][0]['course_id']=='MA101'

def test_published_only(client):
    data=get(client,{'outline_status':'published'}).json()['data']
    assert data['total']==3 and all(r['outline_published'] for r in data['items'])

def test_unpublished_only(client):
    data=get(client,{'outline_status':'unpublished'}).json()['data']
    assert data['total']==1 and data['items'][0]['course_id']=='AI999'

def test_semester_only(client):
    data=get(client,{'semester':'2026-2027-1'}).json()['data']
    assert data['total']==4

def test_empty_semester(client):
    data=get(client,{'semester':'2025-2026-2'}).json()['data']
    assert data['items']==[] and data['total']==0 and data['stats']['courses']==0

def test_composite_filters(client):
    data=get(client,{'keyword':'SE201','outline_status':'published','semester':'2026-2027-1'}).json()['data']
    assert data['total']==1

def test_pagination(client):
    first=get(client,{'page':1,'page_size':2}).json()['data']
    second=get(client,{'page':2,'page_size':2}).json()['data']
    assert first['total']==second['total']==4
    assert first['total_pages']==second['total_pages']==2
    assert len(first['items'])==len(second['items'])==2
    assert {x['offering_id'] for x in first['items']}.isdisjoint(x['offering_id'] for x in second['items'])

def test_out_of_range_page(client):
    data=get(client,{'page':9}).json()['data']
    assert data['total']==4 and data['items']==[]

def test_service_directly(client):
    with closing(connect(client.app.state.db_path)) as db:
        data=list_offerings(db,outline_status='unpublished',page_size=1)
        assert data['total']==1

def test_new_offering_reflected_on_existing_data(client):
    with closing(connect(client.app.state.db_path)) as db,db:
        db.execute('INSERT INTO course_offerings(course_id,semester,teaching_class) VALUES (?,?,?)',('SE201','2026-2027-2','软件2404'))
    result=get(client).json()['data']
    assert result['total']==5
    assert result['stats']['courses']==4
    assert get(client,{'semester':'2026-2027-2'}).json()['data']['total']==1

@pytest.mark.parametrize('params',[
    {'page':0},{'page':-1},{'page_size':0},{'page_size':101},
    {'page':'abc'},{'page_size':'a'}, {'outline_status':'unknown'},
    {'semester':'wrong'}, {'semester':'2026-2028-1'},
    {'semester':'2026-2027-3'}, {'keyword':'x'*81},
])
def test_invalid_parameters(client,params):
    response=get(client,params)
    assert response.status_code==422
    assert response.json()['code']=='PARAM_INVALID'

@pytest.mark.parametrize('headers,code,status',[
    ({},'AUTH_REQUIRED',401),
    ({'X-Demo-User':'WRONG'},'USER_UNKNOWN',401),
    ({'X-Demo-User':'S2024001'},'ROLE_FORBIDDEN',403),
    ({'X-Demo-User':'T003'},'ROLE_FORBIDDEN',403),
    ({'X-Demo-User':'D001'},'ROLE_FORBIDDEN',403),
])
def test_forbidden_users(client,headers,code,status):
    response=get(client,headers=headers)
    assert response.status_code==status and response.json()['code']==code

def test_read_only_api(client):
    for method in ('post','put','patch','delete'):
        response=getattr(client,method)(BASE,headers=HEAD,json={'name':'篡改'}) if method!='delete' else client.delete(BASE,headers=HEAD)
        assert response.status_code==405

def test_search_special_characters_are_literal(client):
    assert get(client,{'keyword':'%'}).json()['data']['total']==0
    assert get(client,{'keyword':'_'}).json()['data']['total']==0
    assert get(client,{'keyword':"' OR 1=1 --"}).json()['data']['total']==0

def test_xss_like_keyword_does_not_echo(client):
    value='<script>alert(1)</script>'
    response=get(client,{'keyword':value})
    assert response.status_code==200
    assert value not in response.text

def test_empty_without_teachers(client):
    with closing(connect(client.app.state.db_path)) as db,db:
        db.execute('INSERT INTO courses(id,name,teacher_name,credits,outline_published) VALUES (?,?,?,?,?)',('XX123','未分配教师','待定',2,0))
        db.execute('INSERT INTO course_offerings(course_id,semester,teaching_class) VALUES (?,?,?)',('XX123','2026-2027-1','试验班'))
    data=get(client,{'keyword':'XX123'}).json()['data']
    assert data['total']==1 and data['items'][0]['teachers']=='暂无授课教师'


def test_filter_options_load_from_real_database(client):
    response = client.get(BASE + '/filters', headers={'X-Demo-User': 'V001'})
    assert response.status_code == 200
    data = response.json()['data']
    assert '2026-2027-1' in data['semesters']
    assert any(row['id'] == 'CS101' for row in data['courses'])


def test_filter_options_reject_other_roles(client):
    for identity in ['S2024001', 'D001', 'T003']:
        response = client.get(BASE + '/filters', headers={'X-Demo-User': identity})
        assert response.status_code == 403


def test_filter_options_reject_missing_identity(client):
    response = client.get(BASE + '/filters')
    assert response.status_code in (401, 403)

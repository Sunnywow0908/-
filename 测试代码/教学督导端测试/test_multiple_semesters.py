"""真实演示模式：学期筛选、双督导身份及跨学期检查意见隔离。"""
from fastapi.testclient import TestClient
from main import create_app

BASE='/api/v1/supervisors/me/offerings'

def test_demo_semesters_and_roles(tmp_path):
    with TestClient(create_app(tmp_path/'demo.sqlite3', demo_history=True)) as client:
        for uid in ('V001','V002'):
            h={'X-Demo-User':uid}
            r=client.get(BASE+'/filters',headers=h)
            assert r.status_code==200
            semesters=r.json()['data']['semesters']
            assert semesters==['2026-2027-2','2026-2027-1','2025-2026-2','2025-2026-1','2024-2025-2']
            for semester in semesters:
                data=client.get(BASE,headers=h,params={'semester':semester}).json()['data']
                assert data['total']>0 and all(i['semester']==semester for i in data['items'])
        html=client.get('/supervisor').text
        assert '督导乙' in html and '学生甲（权限验证）' not in html and '主任甲（权限验证）' not in html

def test_review_isolated_by_semester(tmp_path):
    with TestClient(create_app(tmp_path/'demo.sqlite3', demo_history=True)) as client:
        h={'X-Demo-User':'V002'}
        first=client.get(BASE,headers=h,params={'semester':'2025-2026-2'}).json()['data']['items'][0]['offering_id']
        second=client.get(BASE,headers=h,params={'semester':'2026-2027-1'}).json()['data']['items'][0]['offering_id']
        url=f'{BASE}/{first}/inspections'
        payload={'category':'常规检查','conclusion':'正常','content':'本学期课程开设情况符合预期。'}
        assert client.post(url,headers=h,json=payload).status_code==201
        assert len(client.get(url,headers=h).json()['data'])==1
        assert client.get(f'{BASE}/{second}/inspections',headers=h).json()['data']==[]

def test_historical_seed_idempotent(tmp_path):
    from 功能代码及实际项目文件.教研室主任端.demo_semesters import seed_extra_semesters
    from 功能代码及实际项目文件.公共基础模块.db import connect
    from contextlib import closing
    db=tmp_path/'demo.sqlite3'
    with TestClient(create_app(db, demo_history=True)) as client:
        first=client.get(BASE,headers={'X-Demo-User':'V001'}).json()['data']['total']
        seed_extra_semesters(db)
        second=client.get(BASE,headers={'X-Demo-User':'V001'}).json()['data']['total']
        assert first==second==14

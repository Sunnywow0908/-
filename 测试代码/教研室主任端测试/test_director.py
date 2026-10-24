"""US-04、US-05业务单元测试与正常路径集成测试。"""
from contextlib import closing
from fastapi.testclient import TestClient
from main import create_app
from 功能代码及实际项目文件.公共基础模块.db import connect, initialize_database
from 功能代码及实际项目文件.教研室主任端.data import initialize_director
from 功能代码及实际项目文件.教研室主任端 import service

BASE = '/api/v1/directors/me/'
HEAD = {'X-Demo-User':'D001'}


def test_course_service_uses_existing_assignments(client):
    with closing(connect(client.app.state.db_path)) as conn:
        items=service.list_courses(conn,'D001')
        assert {(r['teacher_id'],r['course_id']) for r in items}=={
            ('T002','CS101'),('T003','SE201'),('T003','MA101'),('T005','AI999')}
        assert len(items)==4
        assert next(r for r in items if r['course_id']=='MA101')['duty']=='协讲'
        assert service.get_course(conn,'D001','SE201')['teachers']==[
            {'teacher_id':'T003','teacher_name':'张老师','duty':'主讲'}]


def test_teacher_scope_includes_unassigned_teacher(client):
    data=client.get(BASE+'teachers',headers=HEAD).json()['data']
    assert {r['teacher_id'] for r in data['items']}=={'T001','T002','T003','T005'}
    assert data['total']==4


def test_course_list_api(client):
    response=client.get(BASE+'courses',headers=HEAD)
    assert response.status_code==200
    assert response.json()['code']=='OK'
    assert response.json()['data']['total']==4


def test_teacher_course_filter(client):
    data=client.get(BASE+'courses?teacher_id=T003',headers=HEAD).json()['data']
    assert {r['course_id'] for r in data['items']}=={'SE201','MA101'}


def test_summary_api(client):
    data=client.get(BASE+'courses/CS101/summary',headers=HEAD).json()['data']
    assert data['summary_available'] is True
    assert data['teachers'][0]['teacher_name']=='李老师'
    assert '数据结构' in data['summary']


def test_offering_service_filters(client):
    with closing(connect(client.app.state.db_path)) as conn:
        result=service.list_offerings(conn,'D001','T003','2026-2027-1')
        assert {r['course_id'] for r in result}=={'SE201','MA101'}
        assert next(r for r in result if r['course_id']=='MA101')['teaching_class']=='联合2401'
        assert service.list_offerings(conn,'D001',semester='2025-2026-2')==[]


def test_offerings_api(client):
    data=client.get(BASE+'offerings',headers=HEAD).json()['data']
    assert data['total']==4
    assert all(r['semester']=='2026-2027-1' for r in data['items'])


def test_no_courses_teacher(client):
    for endpoint in ['courses','offerings']:
        response=client.get(BASE+endpoint+'?teacher_id=T001',headers=HEAD)
        assert response.status_code==200
        assert response.json()['data']=={'total':0,'items':[]}


def test_empty_department(client):
    for endpoint in ['teachers','courses','offerings']:
        response=client.get(BASE+endpoint,headers={'X-Demo-User':'D003'})
        assert response.status_code==200
        assert response.json()['data']=={'total':0,'items':[]}


def test_multiple_teachers_same_course_remain_distinct(client):
    # 增加第二个主任范围后，MA101的主讲和协讲各显示一条，不丢失关系。
    with closing(connect(client.app.state.db_path)) as conn,conn:
        conn.execute('INSERT INTO director_scopes VALUES (?,?)',('D001','MA'))
    rows=client.get(BASE+'offerings',headers=HEAD).json()['data']['items']
    math=[r for r in rows if r['course_id']=='MA101']
    assert {(r['teacher_id'],r['duty']) for r in math}=={('T003','协讲'),('T004','主讲')}
    detail=client.get(BASE+'courses/MA101/summary',headers=HEAD).json()['data']
    assert len(detail['teachers'])==2


def test_multiple_scopes_do_not_duplicate_rows(client):
    with closing(connect(client.app.state.db_path)) as conn,conn:
        conn.execute('INSERT INTO director_scopes VALUES (?,?)',('D001','EMPTY'))
    assert client.get(BASE+'offerings',headers=HEAD).json()['data']['total']==4


def test_multiple_classes_and_semesters(client):
    with closing(connect(client.app.state.db_path)) as conn,conn:
        conn.executemany('INSERT INTO course_offerings(course_id,semester,teaching_class) VALUES (?,?,?)',[
            ('SE201','2026-2027-1','软件2404'),('SE201','2026-2027-2','软件2405')])
    data=client.get(BASE+'offerings?teacher_id=T003&semester=2026-2027-2',headers=HEAD).json()['data']
    assert data['total']==1
    assert data['items'][0]['teaching_class']=='软件2405'


def test_teacher_update_is_reflected_after_publication(client):
    teacher={'X-Demo-User':'T005'}
    prefix='/api/v1/teachers/me/courses/AI999/outline'
    response=client.put(prefix,headers=teacher,json={
        'summary':'新的课程简介','objectives':'学习目标','chapters':'章节内容','assessment':'实验考核'})
    assert response.status_code==200
    assert client.post(prefix+'/publish',headers=teacher).status_code==200
    data=client.get(BASE+'courses/AI999/summary',headers=HEAD).json()['data']
    assert data['summary']=='新的课程简介'
    assert data['summary_available'] is True


def test_page_and_openapi(client):
    page=client.get('/director')
    assert page.status_code==200
    assert '教师课程简介' in page.text and '教师开课情况' in page.text
    paths=client.get('/openapi.json').json()['paths']
    assert BASE+'courses' in paths
    assert BASE+'offerings' in paths


def test_initialization_is_idempotent(client):
    initialize_director(client.app.state.db_path)
    initialize_director(client.app.state.db_path)
    assert client.get(BASE+'offerings',headers=HEAD).json()['data']['total']==4


def test_seed_false_creates_empty_tables(tmp_path):
    path=tmp_path/'empty.sqlite3'
    with TestClient(create_app(path,seed=False)) as client:
        assert client.get('/api/v1/health').status_code==200
    with closing(connect(path)) as conn:
        for table in ['users','director_departments','director_scopes','teacher_departments','course_offerings']:
            assert conn.execute('SELECT count(*) FROM '+table).fetchone()[0]==0


def test_original_database_can_be_upgraded(tmp_path):
    path=tmp_path/'old.sqlite3'
    initialize_database(path)
    initialize_director(path)
    with closing(connect(path)) as conn:
        assert conn.execute('SELECT count(*) FROM course_teachers').fetchone()[0]==5
        assert conn.execute('SELECT count(*) FROM enrollments').fetchone()[0]==5
        assert conn.execute('SELECT count(*) FROM director_scopes').fetchone()[0]==3


def test_new_seed_does_not_overwrite_user_assignments(client):
    with closing(connect(client.app.state.db_path)) as conn,conn:
        conn.execute('UPDATE teacher_departments SET department_id=? WHERE teacher_id=?',('MA','T002'))
        conn.execute('UPDATE course_offerings SET teaching_class=? WHERE course_id=?',('修改后的班级','SE201'))
    initialize_director(client.app.state.db_path)
    with closing(connect(client.app.state.db_path)) as conn:
        assert conn.execute('SELECT department_id FROM teacher_departments WHERE teacher_id=?',('T002',)).fetchone()[0]=='MA'
        assert conn.execute('SELECT teaching_class FROM course_offerings WHERE course_id=?',('SE201',)).fetchone()[0]=='修改后的班级'

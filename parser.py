import requests
from typing import List, Tuple
import re
from lxml.html import document_fromstring
import os

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0'})

main_link = 'https://passport.yandex.ru'
lyceum_url = 'https://lyceum.yandex.ru'
login = input('Логин:')
password = input('Пароль')

class Material:
    def __init__(self, lesson, name, material_id) -> None:
        self.lesson: Lesson = lesson
        self.name = name
        self.id = material_id
        self.content = ''

    
    def load_content(self, session:requests.Session):
        data = session.get(f'https://lyceum.yandex.ru/api/student/materials/{self.id}', 
                            params={'groupId': self.lesson.cource.group, 'lessonId': self.lesson.id})
        self.content = data.json()['detailedMaterial']['content']
    
    def save(self):
        with open(f'{self.name}.html', 'w') as file:
            file.write(self.content)
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name

class Lesson:
    def __init__(self, name, lesson_id, cource, tasks, progress,) -> None:
        self.name = name
        self.id = lesson_id
        self.cource: Course = cource
        self.tasks_count = tasks
        self.progress = progress
        self.tasks = []
        self.materials : List[Material] = []
    
    def load_materials(self, session:requests.Session):
        data = session.get('https://lyceum.yandex.ru/api/materials', params={'lessonId': self.id})
        for material_data in data.json():
            material = Material(self, material_data['title'], material_data['id'])
            material.load_content(session)
            print(material)
            self.materials.append(material)
        return self.materials
            
    
    def save(self):
        os.mkdir(self.name)
        os.chdir(self.name)
        os.mkdir('materials')
        os.chdir('materials')
        for material in self.materials:
            material.save()
        os.chdir('../')
        os.chdir('../')
        
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name

class Course:
    def __init__(self, name, link) -> None:
        self.name = name
        self.link = link
        self.lessons : List[Lesson] = []
        self.id = re.findall(r'courses\/(\d+)\/', self.link)[0]
        self.group = re.findall(r'groups\/(\d+)', self.link)[0]
    
    def load_lessons(self, session:requests.Session):
        data = session.get(f'https://lyceum.yandex.ru/api/student/lessons', params={'courseId': self.id, 'groupId': self.group})
        for lesson_data in data.json():
            lesson = Lesson(lesson_data['title'],
                            lesson_data['id'],
                            self,
                            lesson_data['numTasks'],
                            lesson_data['numPassed'])
            lesson.load_materials(session)
            print(lesson)
            self.lessons.append(lesson)
        return self.lessons
    
    def save(self):
        os.mkdir(self.name)
        os.chdir(self.name)
        for lesson in self.lessons:
            lesson.save()
        os.chdir('../')
        
    
    def __repr__(self) -> str:
        return self.name
    
    def __str__(self) -> str:
        return self.name

def find_auth_data(html:str) -> Tuple[str, str]:
    csrf_token = re.search('"csrf":".*?"', html)
    csrf_token = html[csrf_token.start():csrf_token.end()][8:-1]
    process_uuid = re.search('process_uuid=.*?"', html)
    process_uuid = html[process_uuid.start():process_uuid.end()][13:-1]
    return csrf_token, process_uuid

def auth(login, password):
    data = get('auth/')
    csrf_token, proc_id = find_auth_data(data.text)

    auth_login = post('registration-validations/auth/multi_step/start',
                               data={'csrf_token': csrf_token,
                                     'process_uuid': proc_id,
                                     'login': login}).json()
    
    auth_password = post('registration-validations/auth/multi_step/commit_password',
                                  data={'csrf_token': csrf_token,
                                        'track_id': auth_login['track_id'],
                                        'password': password}).json()
    
    user_data = post('registration-validations/auth/accounts',
                              data={'csrf_token': csrf_token}).json()
    return user_data

def get_cources():
    html = session.get('https://lyceum.yandex.ru/').text
    print(html, file=open('test.html', 'w'))
    doc = document_fromstring(html)
    cources_containers = doc.xpath('//li[@class="courses__list-item"]')
    cources = list(map(lambda node: Course(node.xpath('./a/h4/text()')[0], lyceum_url + node.xpath('./a/@href')[0]), cources_containers))
    return cources


def get(url, **kwargs):
    return session.get(f'{main_link}/{url}', **kwargs)

def post(url, **kwargs):
    return session.post(f'{main_link}/{url}', **kwargs)



user_data = auth(login, password)

cources = get_cources()
print('введите номер купса из списка ниже:')
for num, cource in enumerate(cources):
    print(f'{num}) {cource}')
cource_id = int(input())

cources[cource_id].load_lessons(session)
cources[cource_id].save()
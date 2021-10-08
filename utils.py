from typing import Union
from selenium import webdriver
import pymysql
from configparser import ConfigParser
import os
import xlrd
from copy import deepcopy
import random
import time
import logging
from datetime import datetime
from urllib.parse import urljoin
from lxml import etree
from selenium.webdriver import Chrome

class MyDriver(Chrome):
    def get_html(self):
        '''
        获得网页的HTML, 结果经过etree.HTML函数处理后返回.
        '''
        html = self.execute_script("return document.documentElement.outerHTML")
        html = etree.HTML(html)
        return html

def get_driver() -> MyDriver:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images":2})
    options.add_argument("start-maximized")
    options.add_argument('--ignore-certificate-errors')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = MyDriver(options=options)
    return driver

def get_config() -> dict:
    config = ConfigParser()
    config.read(os.path.abspath(__file__) + '/../config.ini')
    return config._sections

def get_table_name() -> str:
    config = ConfigParser()
    config.read(os.path.abspath(__file__) + '/../config.ini')
    return config._sections['mysql']['table_name']

def get_conn():
    info = get_config()['mysql']
    conn = pymysql.connect(
        user = info['username'],
        password = info['password'],
        host = info['host'],
        port = int(info['port']),
        database = info['database']
        )
    return conn

class Spider:
    def __init__(self, path: Union[str, list], driver = None, test:bool = False) -> None:
        '''
        参数:
            path: xpath文件的路径，可为单个文件/多个文件，对应类型str/list
            driver: 要操作的ChromeDriver的实例对象
        关于xpath文件:
            xpath文件为.xls或.xlsx
            文件名为校名
            每行数据共7列，不足7列的自动补足到7列
        关于每行数据:
            第1列为院名，可指定具体的系，以"/"隔开 (如: 化学院/生物化学系)，如果在之后的第6列中有指定系名，以第6列为准
            第2列为要爬取的url，多个url以换行符"\n"隔开。以"["开头和以"]"结尾的，作为列表生成式处理
            第3列为教师，xpath语句要保证隔离开每一个教师，指向的是节点元素，而非节点的属性。如果指向的是a标签节点，自动提取@href作为老师详情页url。在第三列为空的情况下，以当前节点下的所有text()拼接作为教师名
            第4列为教师名，xpath要以第2列指向的元素作为根节点。在第2列的节点所含文本为教师名的情况下，可省略不写
            第5列为职称
            第6列为系
            第7列为教师专长或研究方向
        '''
        logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(name)s - %(levelname)s \n\t%(message)s')
        self.table_name = get_table_name()
        self.driver = driver if driver else get_driver()
        self.path = path
        self.conn = get_conn()
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.FileHandler(os.path.abspath(__file__) + "/../log/{0}.txt".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H-%M-%S"))))
        self.logger.setLevel(level = logging.INFO)
        self.count = {'succeed': 0, 'failed': 0}
        self.test_mode = test

    def set_path(self, path: Union[str, list]) -> None:
        self.path = path

    def _parse_path(self) -> None:
        if type(self.path) == str:
            self.path = [self.path]
            return
        if type(self.path) != list:
            raise TypeError("type of self.path must be list!")

    def _values_normalizing(self, values: list) -> list:
        '''
        补全数据列表大小至7
        '''
        if (length := len(values)) <= 7:
            result = deepcopy(values) + (7 - length) * [None]
            return result
        else:
            self.logger.warning("表数据列数大于7")
        return values

    def _item_check(self, item: dict) -> dict:
        res = {}
        lost = []
        for key in item:
            res[key] = item[key][0] if item[key][0] else None
            if item[key][1]:
                if not item[key][0]:
                    lost.append(key)

        if lost:
            lost_str = "item丢失字段 " + "【%s】  " * len(lost) %tuple(lost)
            for i in res:
                if i in lost:
                    lost_str += "\n\t" + "{0} : {1} -- {2}".format('【' + i + '】', res[i], item[i][1])
                else:
                    lost_str += "\n\t" + "{0} : {1} -- {2}".format(i, res[i], item[i][1])
            self.logger.warning(lost_str)

        return res



    def _write(self, item: dict) -> None:
        if not self.test_mode:
            try:
                self.cursor.execute(
                    'insert into {0} (school, faculty, name, title, subject, curriculum, introduction) values(%s,%s,%s,%s,%s,%s,%s)'.format(self.table_name),
                    (item['school'], item['faculty'],item['name'],item['title'],item['subject'],item['cur'],item['url'])
                )
                self.conn.commit()
                self.count['succeed'] += 1
            except:
                self.conn.rollback()
                self.logger.error('method: Spider._write ERROR!', exc_info=True)
                self.count['failed'] += 1
        else:
            self.count['succeed'] += 1
            return

    def _url_check(self, burls: str) -> list:
        urls = [i for i in burls.split('\n') if i]
        result = []
        for i in urls:
            if i[0] == '[' and i[-1] == ']':
                result += eval(i)
            else:
                if i not in result:
                    result.append(i)
                else:
                    self.logger.warning('存在重复的URL: %s' %i)
        return result

    def _iframe(self, iframe_str: str) -> None:
        iframe = self.driver.find_element_by_xpath(iframe_str.strip())
        if not iframe:
            self.logger.error("未找到iframe元素!")
            raise BaseException()
        else:
            self.driver.switch_to.frame(iframe)

    def test_on(self) -> bool:
        self.test_mode = True
        return self.test_mode

    def test_off(self) -> bool:
        self.test_mode = False
        return self.test_mode

    def run(self) -> None:
        item = {}
        self.count = {'succeed': 0, 'failed': 0}
        self._parse_path()
        for path in self.path:
            rb = xlrd.open_workbook(path)
            rs = rb.sheet_by_index(0)
            school = os.path.basename(path).split('.')[0]
            self.logger.info("开始爬取：{0} 【测试模式:{1}】".format(school, {False:'OFF', True:'ON'}[self.test_mode]))
            for i in range(rs.nrows):
                faculty = None
                subject = None
                iframe = None
                values = self._values_normalizing(rs.row_values(i))
                burls = values[1]
                burls = self._url_check(burls)
                faculty, subject = values[0].split('=>') if len(values[0].split('=>')) == 2 else [values[0], None]
                if '#iframe' in faculty:
                    faculty, iframe = faculty.split('#iframe')
                base_xpath = values[2]
                name_xpath = values[3]
                title_xpath = values[4]
                subject_xpath = values[5]
                cur_xpath = values[6]

                for burl in burls:
                    name = None
                    title = None
                    cur = None
                    url = None
                    self.driver.get(burl)
                    time.sleep(random.uniform(0.6,1.2))
                    if iframe:
                        try:
                            self._iframe(iframe)
                        except:
                            self.logger.error("faculty={0}\nburl={1}".format(faculty, burl))
                            continue
                    html = self.driver.execute_script("return document.documentElement.outerHTML")
                    html = etree.HTML(html)
                    a = html.xpath(base_xpath)
                    if not a:
                        self.logger.error('网页爬取失败,未找到教师: %s' %burl)
                        self.count['failed'] += 1
                        continue

                    for t in a:
                        if base_xpath and name_xpath:
                            name = ''.join(t.xpath(name_xpath)).strip()
                        else:
                            name = ''.join(t.xpath('.//text()')).strip()

                        if not name:
                            continue

                        if t.tag == 'a':
                            if t.get('href'):
                                url = urljoin(burl, t.get('href'))
                            else:
                                url = None

                        if title_xpath:
                            if title_xpath[0] not in ['.', '/']:
                                title = title_xpath
                            else:
                                title = ''.join(t.xpath(title_xpath)).strip()

                        if subject_xpath:
                            if subject_xpath[0] not in ['.', '/']:
                                subject = subject_xpath
                            else:
                                subject = ''.join(t.xpath(subject_xpath)).strip()

                        if cur_xpath:
                            if cur_xpath[0] not in ['.', '/']:
                                cur = cur_xpath
                            else:
                                cur = ''.join(t.xpath(cur_xpath)).strip()

                        item['school'] = [school, None]
                        item['faculty'] = [faculty, None]
                        item['name'] = [name, name_xpath]
                        item['title'] = [title, title_xpath]
                        item['subject'] = [subject, subject_xpath]
                        item['cur'] = [cur, cur_xpath]
                        item['url'] = [url, None]
                        item = self._item_check(item)
                        self._write(item)

            self.logger.info("========================================================")
            self.logger.info("成功获取: %d, 网页失败: %d" %(self.count['succeed'], self.count['failed']))


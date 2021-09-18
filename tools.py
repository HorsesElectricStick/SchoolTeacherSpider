from typing import Literal, Union
import pymysql
from lxml import etree
import requests
from requests_html import HTMLSession
from selenium import webdriver
import re
import random
from selenium.webdriver import Chrome

class MyDriver(Chrome):
    def get_html(self):
        '''
        获得网页的HTML, 结果经过etree.HTML函数处理后返回.
        '''
        html = self.execute_script("return document.documentElement.outerHTML")
        return etree.HTML(html)

def randf():
    return random.uniform(0.6, 1.3)

# 标准插入语句
_sql = 'insert into teacher (school, faculty, name, title, subject, curriculum, introduction) values(%s,%s,%s,%s,%s,%s,%s)'

def only_chinese(s):
    '''
    移除所有非中文字符
    '''
    s = re.sub('[^\u4e00-\u9fa5]+',' ',s)
    return s.strip()

def conn():
    conn = pymysql.connect(user='root', password='sseawayss', host='localhost', database='teacher')
    return conn

def get_driver():
    # chrome_options.add_argument("--headless")

    # options = webdriver.ChromeOptions()
    # options.add_argument("start-maximized")
    # options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # options.add_experimental_option("useAutomationExtension", False)
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # driver = webdriver.Chrome(options=options)
    # with open(r"C:\Users\ilove\Desktop\stealth.min.js") as f:
    #     js = f.read()
    # driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #     "source": js
    # })
    
    options = webdriver.ChromeOptions()
    # options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images":2})
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = MyDriver(options=options)
    # stealth(driver,
    #     vendor="Google Inc.",
    #     platform="Win32",
    #     webgl_vendor="Intel Inc.",
    #     renderer="Intel Iris OpenGL Engine",
    #     fix_hairline=True,
    #     )
    # with open(r"C:\Users\ilove\Desktop\stealth.min.js") as f:
    #     js = f.read()
    #     driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #         "source": js
    #     })
    return driver

def nameparse(s, mark=None) -> list:
    '''
    对人名字符串进行解析，将人名切割和合并，mark为切割标记字符
    主要针对 *有空格的二字人名* 所组成的混合字符串
    如:
        string = "张三 李 四   王 五  张某人 李  某"
        nameparse(string) -> ['张三', '李四', '王五', '张某人', '李某']
    并不适用于所有情况，该方法会打印解析后人名的数量以供校对
    已知不适用的情况:
        (1) 有空格的三字人名
            string = "张三 李 四   王 五  张某 人 李  某"
            nameparse(string) -> ['张三', '李四', '王五', '张某', '人李']
        (2) 有空格的英文名
            string = "张三 李 四   王 五  张某人 李  某 Peter Park"
            nameparse(string) -> ['张三', '李四', '王五', '张某人', '李某', 'Peter', 'Park']
    注意事项:
        (1) 结果会进行去重，如有同名不同人的情况，需添加标记，如 "张三 张三" 更改为 "张三(大) 张三(小)"
    '''
    if mark:
        names = s.split(mark)
    else:
        names = s.split()
    result = []
    for i in range(len(names)):
            if i > 0:
                    if len(names[i]) == 1 and len(names[i-1]) == 1:
                            result.append(names[i-1]+names[i])
                            names[i] = names[i-1]+names[i]
            if len(names[i]) > 1:
                    result.append(names[i])
    final_result = list(set(result))
    final_result = [i.strip() for i in final_result]
    final_result.sort(key=result.index)
    print('total:%d' %len(final_result))
    return final_result

def wparse(url: str, xpath: Union[str, list, tuple]) -> list:
    '''
    基于webdriver的爬虫接口
    '''
    driver = webdriver.Chrome()
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
          "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
        })
    driver.get(url)
    html = driver.execute_script("return document.documentElement.outerHTML")
    html = etree.HTML(html)
    result = []
    if type(xpath) == str:
        driver.quit()
        return html.xpath(xpath)
    for i in xpath:
        result.append(html.xpath(i))
    driver.quit()
    return result

def qparse(url: str, xpath: Union[str, list, tuple], inputType: Literal['t', 'c'] = 'c') -> list:
    '''
    基于requests的爬虫接口
    inputType
    '''
    try:
        res = requests.get(url=url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'})
        if inputType == 'c':
            html = etree.HTML(res.content)
        elif inputType == 't':
            html = etree.HTML(res.text)
        else:
            raise ValueError('未知的模式: \'%s\'' %inputType)
        result = []
        if type(xpath) == str:
            return html.xpath(xpath)
        for i in xpath:
            result.append(html.xpath(i))
        return result
    except:
        return []

class StatusCodeError(Exception):
    '''
    状态码异常
    '''
    def __init__(self, msg):
        self.message = msg

    def __str__(self) -> str:
        return "Status Code is {0}".format(self.message)

def jparse(url):
    '''
    对json_api使用的爬虫接口
    '''
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise StatusCodeError(res.status_code)
    else:
        return res.json()

def parse(url: str, xpath: Union[str, list, tuple]) -> list:
    try:
        session = HTMLSession()
        session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        r = session.get(url)
        r.html.render()
        if type(xpath) in (list, tuple):
            result = []
            for x in xpath:
                result.append(r.html.xpath(x))
            session.close()
            return result
        session.close()
        return r.html.xpath(xpath)
    except:
        session.close()
        return []

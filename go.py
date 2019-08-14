from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import time
from retry import retry
import random
import json
import sys
from math import exp, pi
import urllib.parse
import requests


def bar(n, l, long=50, pre='', done='=', head='>', blank='.'):
    print(pre+'[{}]{}%'.format((int(n/l*long)*done +
                                head+blank*long)[0:long], round(n/l*100, 2),))
    return n+1


def LoadConf():
    global Conf
    global TEST
    global JDBeanModelON
    global JDTryModelON
    global ServerAddr

    global DriverCleanN
    global MaxDriverCleanN
    global UserSaveN
    global MaxUserSaveN
    global MaxGroupNumber

    global LeastOnlineTime
    global EachUpdateShopAmount
    global TryDataGap
    global UserLoginStatusTestGap
    global BeanWaitTime

    DriverCleanN = 0
    UserSaveN = 0
    MaxUserSaveN = 100
    MaxGroupNumber = 10

    try:
        # 尝试载入
        with open('data/conf.json') as f:
            Conf = json.load(f)

        TEST = Conf['TEST']
        JDTryModelON = Conf['JDTryModelON']
        JDBeanModelON = Conf['JDBeanModelON']
        ServerAddr = Conf['ServerAddr']
        MaxDriverCleanN = Conf['MaxDriverCleanN']
        LeastOnlineTime = Conf['LeastOnlineTime']
        EachUpdateShopAmount = Conf['EachUpdateShopAmount']
        TryDataGap = Conf['TryDataGap']
        UserLoginStatusTestGap = Conf['UserLoginStatusTestGap']
        BeanWaitTime = Conf['BeanWaitTime']

    except Exception as e:

        Conf = {
            'TEST': False,
            'JDTryModelON': True,
            'JDBeanModelON': True,
            'JDTryModelON': True,
            'JDBeanModelON': True,
            'ServerAddr': 'http://111.231.78.78:1231/api/',
            'MaxDriverCleanN': 20,
            'LeastOnlineTime': 12,
            'EachUpdateShopAmount': 1,
            'TryDataGap': 1,
            'UserLoginStatusTestGap': 30,
            'BeanWaitTime': 1,
        }

        TEST = Conf['TEST']
        JDTryModelON = ['JDTryModelON']
        JDBeanModelON = ['JDBeanModelON']
        ServerAddr = Conf['ServerAddr']
        MaxDriverCleanN = Conf['MaxDriverCleanN']
        LeastOnlineTime = Conf['LeastOnlineTime']
        EachUpdateShopAmount = Conf['EachUpdateShopAmount']
        TryDataGap = Conf['TryDataGap']
        UserLoginStatusTestGap = Conf['UserLoginStatusTestGap']
        BeanWaitTime = Conf['BeanWaitTime']
        with open('data/conf.json', 'w') as f:
            json.dump(Conf, f, ensure_ascii=False, indent=2)
        print(str(e))
        print('Using default Conf !')
        print(Conf)


def get_driver(headless=True, nopic=True, nostyle=True):
    systemtype = sys.platform
    fireFoxOptions = webdriver.FirefoxOptions()
    firefox_profile = webdriver.FirefoxProfile()

    if not TEST:
        if headless:
            # 无头模式
            fireFoxOptions .add_argument("--headless")
        if nopic:
            # 不加载图片
            firefox_profile.set_preference("permissions.default.image", 2)
        if nostyle:
            # 禁用样式表文件
            firefox_profile.set_preference("permissions.default.stylesheet", 2)
    # 更新设置
    firefox_profile.update_preferences()
    # 系统判断
    if systemtype == 'linux':
        executable_path = './data/geckodriver'
    elif systemtype == 'win32':
        executable_path = './data/geckodriver.exe'
    else:
        print('不支持的系统类型！')
        raise OSError
    driver = webdriver.Firefox(executable_path=executable_path, firefox_profile=firefox_profile,
                               options=fireFoxOptions, service_log_path='./data/geckodriver.log')

    # 设置最长加载时间
    # driver.set_page_load_timeout(30)
    return driver


def UpdateTryActivity():

    def GetPageAmount():
        @retry(tries=3, delay=1, backoff=2)
        def getpageamount():
            r = requests.get(
                'https://try.jd.com/activity/getActivityList', timeout=10)
            r.raise_for_status
            listsoup = BeautifulSoup(r.text, 'html.parser')
            pageamount = int(listsoup.find_all(
                'span', {'class': 'fp-text'})[0].i.text)+1

            return pageamount

        print('更新试用数据 ...', end=' ')
        try:
            pageamount = getpageamount()
        except Exception as e:
            print(' in {} .\n{}'.format('getpageamount', str(e)))
            raise Exception
        print(pageamount)
        print('Done .')
        return pageamount

    def getActivityIdList(pageamount):
        @retry(tries=15, delay=1, backoff=2)
        def getListPageText(n):
            r = requests.get(
                'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n), timeout=10)
            return r.text

        @retry(tries=5, delay=1, backoff=2)
        def RemoveExistingActivityId(activity_id_list):
            print('去除服务端已存在的ID ...', end=' ')
            send_data = {
                'Reason': 'RemoveExistingActivityId',
                'ActivityIdList': activity_id_list,
            }
            r = requests.post(ServerAddr, json=send_data)
            r.raise_for_status
            data = r.json()
            print(len(activity_id_list), ' -> ', len(data['ActivityIdList']))
            print('Done .')
            return data['ActivityIdList']

        print('获取需要抓活动ID列表 ...')
        n = 1
        all_activity_id_list = []
        while n <= pageamount:
            n = bar(n, pageamount)
            # 获取 activity_id
            try:
                text = getListPageText(n)
            except Exception as e:
                print('error in {} .\n{}'.format('getListPageText', str(e)))
                continue
            listsoup = BeautifulSoup(text, 'html.parser')
            for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
                # 只获取24h内可以结束的
                # if (int(li.attrs['end_time'])/1000-time.time())/(60*60) < 24:
                all_activity_id_list.append(li.attrs['activity_id'])

        # 消除服务端已保存的的
        try:
            activity_id_list = RemoveExistingActivityId(all_activity_id_list)
        except Exception as e:
            activity_id_list = all_activity_id_list
            print('error in {} .\n{}'.format(
                'RemoveExistingActivityId', str(e)))

        return activity_id_list

    def getattrs(activity_id_list):

        @retry(tries=5, delay=1, backoff=2)
        def get_activity_data(activity_id):
            url = 'https://try.jd.com/migrate/getActivityById?id={}'.format(
                activity_id)
            # print(url)
            r = requests.get(url, timeout=10).json()
            data = r['data']
            return data

        @retry(tries=5, delay=1, backoff=2)
        def get_price(iteminfo):
            url = 'https://p.3.cn/prices/mgets?skuIds=J_{}'.format(
                iteminfo['TrialSkuId'])
            # print(url)
            r = requests.get(url, timeout=10)
            j = r.json()
            return j[0]['p']

        print('获取活动详情 ...')
        trydata = []
        n = 0
        l = len(activity_id_list)
        for activity_id in activity_id_list:
            n = bar(n, l)
            iteminfo = {}

            # 获取各种属性
            try:
                data = get_activity_data(activity_id)
            except Exception as e:
                print('error in {} .\n{}'.format('get_activity_data', str(e)))
                continue

            # 活动属性提取
            iteminfo['ActivityId'] = activity_id
            iteminfo['TrialSkuId'] = data['trialSkuId']
            iteminfo['StartTime'] = data['startTime']/1000
            iteminfo['EndTime'] = data['endTime']/1000
            iteminfo['SupplyCount'] = data['supplyCount']
            iteminfo['TrialName'] = data['trialName']
            try:
                iteminfo['ShopName'] = data['shopInfo']['title']
                iteminfo['ShopId'] = data['shopInfo']['shopId']
            except TypeError:
                print('TypeError when get activity {} shop info '.format(
                    iteminfo['ActivityId']))
                iteminfo['ShopName'] = ''
                iteminfo['ShopId'] = 0

            # 获取价格
            try:
                price = get_price(iteminfo)
            except Exception as e:
                print('error in {} .\n{}'.format('get_price', str(e)))
                price = 25
            iteminfo['Price'] = float(price)

            trydata.append(iteminfo)

        return trydata

    def Update(try_activity_list):

        @retry(tries=5, delay=1, backoff=2)
        def updatetrydata(try_activity_list):
            send_data = {

                'Reason': 'UpdateTryData'
            }

            send_data['TryActivityList'] = try_activity_list
            r = requests.post(ServerAddr, json=send_data)
            # print(r.status_code)
            r.raise_for_status
            data = r.json()
            return data
        print('上传活动数据 ...')
        try:
            updatetrydata(try_activity_list)
        except Exception as e:
            print(' in {} .\n{}'.format('UpdateTryData', str(e)))
        print('Done .')

    # 获取页数
    pageamount = GetPageAmount()
    # 获取 activity_id_list
    need_check_activity_id_list = getActivityIdList(pageamount)
    # 获取活动信息
    try_activity_list = getattrs(need_check_activity_id_list)
    # 上传
    Update(try_activity_list)


def estimate(trydata):
    def loadrule():
        try:
            rule = json.load(open('./data/rule.txt'))
        except:
            rule = {
                '自营': 30,
                '旗舰': 15,
                '价格': 30,
                '数量': 30,
                '优先': 20,
                '排除': 30,
                '优先关键字': ['鼠标', '键盘', '硬盘', '内存', '显卡', '笔记本', '中性笔', '路由器', '智能', 'u盘', '耳机', '音箱', '储存卡'],
                '排除关键字': ['丝袜', '文胸', '舞鞋', '课程', '流量卡', '手机卡', '婴儿', '手机壳', '钢化膜', '润滑油', '纸尿裤', '白酒', '药', '保健品'],
            }
            json.dump(rule, open('./data/rule.txt', 'w'),
                      ensure_ascii=False, indent=4)

            print('can\'t find rule.txt, useing default rule !')
        return rule

    # 载入规则
    rule = loadrule()

    data = []
    for iteminfo in trydata:
        # 计算价值
        def get_shopname_score(shopname):
            return ('自营' in shopname)*rule['自营']+('旗舰' in shopname)*rule['旗舰']

        def get_amount_score(x):
            E = 10  # excpection
            theta = 50
            maxscore = rule['数量']
            fix = exp(-(10-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5)
            return (exp(-(x-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5))*maxscore/fix

        def get_price_score(price):
            maxscore = rule['价格']
            return maxscore*(-exp(-0.01*price)+1)

        def get_key_score(text):
            score = 0
            for key in rule['优先关键字']:
                if key in text:
                    score += rule['优先']
            for key in rule['排除关键字']:
                if key in text:
                    score -= rule['排除']
            return score

        scorelist = [
            get_shopname_score(iteminfo['ShopName']),
            get_price_score(iteminfo['Price']),
            get_amount_score(iteminfo['SupplyCount']),
            get_key_score(iteminfo['TrialName']),
        ]

        # 数据添加
        iteminfo['score'] = sum(scorelist)
        data.append(iteminfo)

    # 按照分数重新排序

    def sort_by_score(item):
        return item['score']
    data.sort(key=sort_by_score, reverse=True)

    return data


def SaveUser(direct=True):
    global UserSaveN
    global USER

    if direct or UserSaveN > MaxUserSaveN:
        print('| Save User ...')

        # 剔除 用户已检查列表 中已过期的店铺
        t = time.time()
        for shopid, check_time in USER['user_shop_check_time_dict'].items():
            if t - check_time > 1 * 24 * 60 * 60:
                del USER['user_shop_check_time_dict'][shopid]

        # 检查文件 如果user存在则删除
        with open('./data/users.json') as f:
            oldusers = json.load(f)
        newusers = []
        for olduser in oldusers:
            if olduser['username'] != USER['username']:
                newusers.append(olduser)
        # 重新添加
        newusers.append(USER)
        # 排序

        def for_sort(user):
            return user['username']
        newusers.sort(key=for_sort)
        # 写入
        with open('./data/users.json', 'w') as f:
            json.dump(newusers, f, ensure_ascii=False, indent=2)

        # print('| done.')
        UserSaveN = 0
    else:
        UserSaveN += 1


def clean_driver(driver, keepcookie=True):

    @retry(tries=15, delay=1, backoff=2)
    def get_page(driver):
        driver.get('https://www.jd.com/')
        return driver

    global DriverCleanN

    if DriverCleanN > MaxDriverCleanN:
        print('| cleaning driver...')
        cookies = driver.get_cookies()
        driver.quit()
        driver = get_driver()
        driver = get_page(driver)
        if keepcookie:
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    if TEST:
                        print(e)
                        print(cookie)

        DriverCleanN = 1
        # print('| Done .')
    else:
        DriverCleanN += 1
    return driver


def login():
    def get_one_user():
        try:
            with open('./data/users.json') as f:
                userlist = json.load(f)
            l = len(userlist)

            if l == 0:
                user = None
            else:
                print('| 找到{}个user'.format(l))
                n = 1
                for user in userlist:
                    print('| {}--{}'.format(n, user['username']))
                    n += 1

                while True:
                    try:
                        user = userlist[int(input('| 输入user编号:'))-1]
                        break
                    except:
                        print('| 输入错误，重新输入')

        except (FileNotFoundError, IndexError):
            user = None
            userlist = []
        except Exception as e:

            print('error in {} .\n{}'.format('| get_one_user', str(e)))
            user = None

        with open('./data/users.json', 'w') as f:
            json.dump(userlist, f, ensure_ascii=False, indent=2)
        return user

    def test_user_cookies_status(user, driver):
        print('| testing {} ...'.format(user['username']))
        testurl = 'https://home.jd.com/'
        url = 'https://jd.com/'
        driver.get(url)
        for cookie in user['cookies']:
            driver.add_cookie(cookie)
        driver.get(testurl)
        current_url = driver.current_url
        if 'passport.jd.com' in current_url:
            logined = False
        elif 'home.jd.com' in current_url:
            logined = True

        else:
            print('unknow user login status !!!!!')
            print(current_url)
            logined = False
        return logined, driver

    def relogin(driver, userid=None, password=None):
        print('| login...')
        driver.quit()
        driver = get_driver(headless=False, nopic=False, nostyle=False)
        driver.set_window_size(350, 350)
        driver.get('https://passport.jd.com/new/login.aspx')

        # 转到账户密码登录
        driver.find_element_by_class_name('login-tab-r').click()

        while not driver.current_url == 'https://www.jd.com/':
            userid_box = driver.find_element_by_id('loginname')
            password_box = driver.find_element_by_id('nloginpwd')
            # 清空输入框
            userid_box.clear()
            password_box.clear()

            # 获取账户密码
            if userid == None or password == None:
                userid = input('输入登录ID：')
                password = input('输入登录密码：')

            userid_box.send_keys(userid)
            password_box.send_keys(password)

            driver.find_element_by_id('loginsubmit').click()

            time.sleep(2)
            if driver.current_url == 'https://www.jd.com/':
                break
            else:
                WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_xpath(
                    '/html/body/div[4]/div/div').is_displayed())
                print('| 滑动以通过验证...')
                WebDriverWait(driver, 120).until_not(lambda driver: driver.find_element_by_xpath(
                    '/html/body/div[4]/div/div').is_displayed())

                # 如果出现错误 打印出信息
                try:
                    msg = driver.find_element_by_class_name('msg-error')
                    if msg.is_displayed():
                        userid = None
                        password = None
                        print(msg.text)
                except:
                    pass

        # 组建出该user
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'unick':
                username = urllib.parse.unquote(cookie['value'])
                break
        user = {
            'username': username,
            'userid': userid,
            'password': password,
            'cookies': cookies,
            'logintime': time.time(),
            'user_shop_check_time_dict': {},
        }
        return driver, user

    print('|-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+--+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
    an = input('| y:载入userlist，n:添加新user\n| >>>')
    driver = get_driver()
    if an == '' or an == 'y':
        user = get_one_user()

        if user != None:
            try:
                if 24*60*60-(time.time()-user['logintime']) > LeastOnlineTime*60*60:
                    logined, driver = test_user_cookies_status(user, driver)
                    if logined:
                        user['cookies'] = driver.get_cookies()
                    else:
                        print('| {} 未登录 !'.format(user['username']))
                        driver, user = relogin(
                            driver, password=user['password'], userid=user['userid'])
                else:
                    print('| {} 登录状态已过期，或可在线时长小于阈值!'.format(user['username']))
                    driver, user = relogin(
                        driver, password=user['password'], userid=user['userid'])
            except KeyError:
                driver, user = relogin(
                    driver, password=user['password'], userid=user['userid'])

        else:
            print('| 未找到任何用户 !')
            driver, user = relogin(driver)

    else:
        print('| 新用户登录 ...')
        driver, user = relogin(driver)

    # USER
    global USER
    USER = user

    # 更新用户列表
    SaveUser()

    driver.quit()
    driver = get_driver()
    driver.get('https://www.jd.com/')
    for cookie in user['cookies']:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            if TEST:
                print(e)
                print(cookie)
    driver.refresh()
    print('|-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+--+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
    print('| Hello {}'.format(user['username']))
    print('|-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+--+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
    return driver


def delfollows(driver):
    if input('| 是否删除关注的店铺(y/n):') in ['y', '']:
        try:
            driver.get('https://t.jd.com/follow/vender/list.do')
            while True:
                driver.find_element_by_link_text('批量操作').click()
                driver.find_element_by_class_name('u-check').click()
                driver.find_element_by_class_name('u-unfollow').click()
                time.sleep(1)
                driver.find_element_by_class_name(
                    'ui-dialog-btn-submit').click()
                time.sleep(1)
        except NoSuchElementException:
            print('| Done .')
        except Exception as e:
            print('error in {}  \n{}'.format('', str(e)))

    return driver


def jdtry(driver):

    @retry(tries=6, delay=1, backoff=2)
    def get_itempage_find_appbtn(driver, item):
        url = 'https://try.jd.com/{}.html'.format(item['ActivityId'])
        driver.get(url)
        btn = driver.find_element_by_class_name('app-btn')
        return btn

    @retry(tries=3, delay=1, backoff=2)
    def get_dialogtext(app_btn, driver):
        app_btn.click()
        time.sleep(random.random()+1)
        dialog = driver.find_element_by_class_name(
            'ui-dialog-content')
        return dialog.text, dialog

    @retry(tries=3, delay=1, backoff=2)
    def click_fellow(dialog):
        dialog.find_element_by_class_name('y').click()
        time.sleep(random.random()*2+4)

    @retry(tries=3, delay=1, backoff=2)
    def GetTryData(TryDataGap):
        send_data = {
            'Reason': 'GetTryData',
            'Days': TryDataGap,
        }

        r = requests.post(ServerAddr, json=send_data)
        r.raise_for_status
        data = r.json()
        return data

    # 获取试用列表
    print('获取试用列表...')

    data = GetTryData(TryDataGap)

    if data['Status']:
        try_activity_list = estimate(data['TryActivityList'])

    else:
        if data['Reason'] == 'TryDataTimeout':
            print(data['Reason'])
            UpdateTryActivity()
            data = GetTryData(TryDataGap)
            try_activity_list = estimate(data['TryActivityList'])
        else:
            print(data)
            raise Exception

    print('Done .')

    print('开始申请京东试用...')

    n = 0
    l = len(try_activity_list)
    for try_activity in try_activity_list:
        n = bar(n, l)
        # get itempage & find app-btn
        try:
            app_btn = get_itempage_find_appbtn(driver, try_activity)
        except Exception as e:
            print(' error in {}  \n{}'.format(
                'get itempage & find app-btn', str(e)))
            continue

        # check if have got
        if '查看更多' not in app_btn.text:
            # get dialogtext
            try:
                dialogtext, dialog = get_dialogtext(app_btn, driver)
            except Exception as e:
                print(' error in {}  \n{}'.format('get dialogtext', str(e)))
                continue

            # fenxi dialogtext
            if '超过上限' in dialogtext:
                print('达到每日上限！')
                break

            elif '申请成功' in dialogtext:
                print('Success ! {}'.format(try_activity['TrialName']))
                time.sleep(random.random()*2+4)

            elif '需关注店铺' in dialogtext:
                try:
                    click_fellow(dialog)
                    print('Success ! {}'.format(try_activity['TrialName']))
                except Exception as e:
                    print(' error in {}  \n{}'.format('clickYES', str(e)))
            else:
                print('infomation:', dialogtext)
        else:
            print('Have got befor!')

        driver = clean_driver(driver)

    return driver


def jdbean(driver):
    @retry(tries=3, delay=1, backoff=2)
    def get_shop_page(shop_id, driver):
        shopurl = 'https://mall.jd.com/index-{}.html'.format(shop_id)
        driver.get(shopurl)
        return driver

    @retry(tries=3, delay=1, backoff=2)
    def GetBeanData(GroupNumber):
        if GroupNumber == 0:
            print('| ******检查优惠更新******')
        else:
            print('| 获取店铺列表 ...', end=' ')
        send_data = {
            'Reason': 'GetBeanData',
            'FirstTime': GroupNumber == 0,
        }

        r = requests.post(ServerAddr, json=send_data)
        # print('| ',r.status_code)
        r.raise_for_status
        data = r.json()
        if not data['Status']:
            print('| ', data)

        print('| ', len(data['ShopList']))
        # print('| Done .')
        return data['ShopList']

    @retry(tries=3, delay=1, backoff=2)
    def UpdateBeanData(shop_id_list_for_update):
        if len(shop_id_list_for_update) >= EachUpdateShopAmount:
            print('| 上传店铺信息 ...')
            send_data = {
                'Reason': 'UpdateBeanData',
                'ShopList': shop_id_list_for_update
            }
            r = requests.post(ServerAddr, json=send_data)
            r.raise_for_status
            data = r.json()
            if data['Status']:
                shop_id_list_for_update = []
            else:
                print('| ', data)
            # print('| Done .')

        return shop_id_list_for_update

    print('|-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+--+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
    print('| 开始获取京豆 ...')

    global USER

    # 用于预存要更新的Shop
    shop_id_list_for_update = []

    # 记录获取组数
    GroupNumber = 0

    while True:

        # 获取一组店铺
        try:
            print(
                '|-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+--+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-',
                len(USER['user_shop_check_time_dict'])
                )

            shop_list = GetBeanData(GroupNumber)

            GroupNumber += 1
            if GroupNumber > MaxGroupNumber:
                GroupNumber = 0
                continue
     
            if len(shop_list) == 0:
                print("| Today's Check Task Done! Sleeping...")
                time.sleep(30)
                continue



            # 每组检查序数
            GroupShopIndex = 1
            for shop in shop_list:
                if str(shop['ShopId']) not in USER['user_shop_check_time_dict']:
                    # 进入店铺主页
                    driver = get_shop_page(shop['ShopId'], driver)

                    # 等待获取优惠
                    try:
                        btn = WebDriverWait(driver, BeanWaitTime).until(
                            lambda d: d.find_element_by_css_selector("[class='J_drawGift d-btn']"))
                        btn.click()
                        got = True
                    except TimeoutException:
                        got = False

                    # 加入用户过检查列表准备保存
                    USER['user_shop_check_time_dict'][str(shop['ShopId'])] = time.time()

                    # 保存用户数据
                    SaveUser(direct=False)

                    # 重置浏览器
                    driver = clean_driver(driver)

                    # 存入上传列表
                    shop_id_list_for_update.append({
                        'ShopId': shop['ShopId'],
                        'Got': got
                    })

                    # 上传店铺数据
                    shop_id_list_for_update = UpdateBeanData(
                        shop_id_list_for_update)


                    # 显示进度
                    # pre='| {: <2} {: <20}'.format(got,shop['ShopName'])
                    bar(
                        GroupShopIndex,
                        len(shop_list),
                        pre='| {: <2} {: <10}'.format(got, shop['ShopId'])
                    )

                GroupShopIndex += 1

        except Exception as e:
            print('| error in {} .\n{}'.format('JDBean', str(e)))
            continue

    return driver


if __name__ == '__main__':
    try:
        # 载入配置
        LoadConf()

        # login
        driver = login()

        # clean follows
        driver = delfollows(driver)

        # try items
        if JDTryModelON:
            driver = jdtry(driver)

        # get bean
        if JDBeanModelON:
            driver = jdbean(driver)

        # quite
        driver.quit()

    except Exception as e:

        print('a fatal error！now quit！')
        print(e)

        # quite
        driver.quit()
        raise

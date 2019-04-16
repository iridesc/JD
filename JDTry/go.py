from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from math import exp, pi
import time
import requests
import re
from retry import retry
import random
import json

def login():
    def get_driver(headless=False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        try:
            driver = webdriver.Chrome('./chromedriver',chrome_options=chrome_options)
        except OSError:
            driver = webdriver.Chrome('./chromedriver.exe',chrome_options=chrome_options)
        
        return driver
    
    driver=get_driver()
    driver.set_window_size(1000, 600)
    driver.get('https://passport.jd.com/new/login.aspx')

    n = 0
    while not driver.current_url == 'https://www.jd.com/':
        time.sleep(1)
        n += 1
        if n > 179:
            driver.refresh()
            print('QR have refreshed !')
            n = 0
        if n % 5 == 0:
            print('Witing for login....{} s '.format(180-n))

    cookies=driver.get_cookies()
    driver.quit()
  

    driver=get_driver(True)
    driver.get('https://passport.jd.com/new/login.aspx')

    for cookie in cookies:
        driver.add_cookie(cookie)
    return driver


def delfollows(driver):
    try:
        driver.get('https://t.jd.com/follow/vender/list.do')
        while True:
            driver.find_element_by_link_text('批量操作').click()
            driver.find_element_by_class_name('u-check').click()
            driver.find_element_by_class_name('u-unfollow').click()
            time.sleep(1)
            driver.find_element_by_class_name('ui-dialog-btn-submit').click()
            time.sleep(1)
    except:
        pass


def jdtry(driver, itemlist):

    @retry(tries=3, delay=2, backoff=2)
    def get_itempage_find_appbtn(driver):
        url = 'https://try.jd.com/{}.html'.format(item['activityid'])
        driver.get(url)
        return driver.find_element_by_class_name('app-btn')
    
    @retry(tries=3, delay=2, backoff=2)
    def get_dialogtext(app_btn):
        app_btn.click()
        time.sleep(random.random()+1)
        dialog = driver.find_element_by_class_name(
            'ui-dialog-content')
        return dialog.text,dialog

    @retry(tries=3, delay=2, backoff=2)
    def click_fellow(dialog):
        dialog.find_element_by_class_name('y').click()
        time.sleep(random.random()*2+4)


    for item in itemlist:
        # get itempage & find app-btn
        try:
           app_btn =get_itempage_find_appbtn(driver)
        except:
            print('erro in get itempage & find app-btn')
            continue

        # check if have got
        if '查看更多' not in app_btn.text:
            # get dialogtext
            try:
                dialogtext,dialog = get_dialogtext(app_btn)
            except:
                print('erro in get dialogtext')
                continue

            # fenxi dialogtext
            if '超过上限' in dialogtext:
                print('Reach the maximum! Now break!')
                break
            
            elif '申请成功' in dialogtext:
                print('Success !')
                time.sleep(random.random()*2+4)
            

            elif '需关注店铺' in dialogtext:
                try:
                    click_fellow(dialog)
                    print('Success !')
                except:
                    print('erro in clickYES')
            
            else:
                print(dialogtext)
        
        else:
            print('Have got befor!')
        

def loaddata():
    def reget():
        t_start = time.time()
        itemlist = []
        # 获取页数
        try:
            r = requests.get('https://try.jd.com/activity/getActivityList')
            r.raise_for_status
            listsoup = BeautifulSoup(r.text, 'html.parser')
            pageamount = int(listsoup.find_all(
                'span', {'class': 'fp-text'})[0].i.text)+1
        except:
            print('error in get page number')

        # 获取从第一页到最后一页的item
        n = 1
        t = 0
        timelist = []
        while n < pageamount:
            # 显示进度与时间
            t = time.time()

            # 获取 activity_id
            activity_id_list = []
            r = requests.get(
                'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n))
            listsoup = BeautifulSoup(r.text, 'html.parser')
            for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
                # 只获取24h内可以结束的
                if (int(li.attrs['end_time'])/1000-time.time())/(60*60) < 24:
                    activity_id_list.append(li.attrs['activity_id'])

            for activity_id in activity_id_list:
                iteminfo = {}
                # 获取各种属性
                try:
                    url='https://try.jd.com/migrate/getActivityById?id={}'.format(activity_id)
                    r = requests.get(url).json()
                    data = r['data']
                except KeyError:
                    print('keyerror in get attrs!')
                    print(url)
                    print(r)
                    continue
                except ConnectionError:
                    print('connectiongerror in get attrs!')
                    print(url)
                    print(r)
                    continue


                iteminfo['activityid'] = activity_id
                iteminfo['trialSkuId'] = data['trialSkuId']
                iteminfo['startTime'] = data['startTime']/1000
                iteminfo['endTime'] = data['endTime']/1000
                iteminfo['supplyCount'] = data['supplyCount']
                iteminfo['trialName'] = data['trialName']
                try:
                    iteminfo['shopname'] = data['shopInfo']['title']
                    iteminfo['shopId'] = data['shopInfo']['shopId']
                except TypeError:
                    print('TypeError when get activity {} shop info '.format(
                        iteminfo['activityid']))
                    iteminfo['shopname'] = ''

                # 获取价格
                try:
                    data = requests.get(
                        'https://p.3.cn/prices/mgets?skuIds=J_{}'.format(iteminfo['trialSkuId'])).json()[0]['p']
                except:
                    print('error in get price!')
                    data = 25
                iteminfo['price'] = float(data)

                # 载入规则
                try:
                    roul = json.load(open('roul.txt'))
                except:
                    roul = {
                        '自营': 30,
                        '旗舰': 15,
                        '价格': 30,
                        '数量': 30,
                        '关键字': 20,
                        '优先关键字': ['鼠标', '键盘', '硬盘', '内存', '显卡', '笔记本', '中性笔', '路由器', '智能', 'u盘', '耳机', '音箱', '储存卡'],
                        '排除关键字': ['丝袜', '文胸', '课程', '流量卡', '婴儿', '手机壳', '润滑油', '纸尿裤', '药', '保健品'],
                    }
                    json.dump(roul, open('roul.txt', 'w'), ensure_ascii=False)

                    print('can\'t find roul.txt, useing default roul !')

                # 计算价值
                def get_shopname_score(shopname):

                    return ('自营' in shopname)*roul['自营']+('旗舰' in shopname)*roul['旗舰']

                def get_amount_score(x):
                    E = 10  # excpection
                    theta = 50
                    maxscore = roul['数量']
                    fix = exp(-(10-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5)
                    return (exp(-(x-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5))*maxscore/fix

                def get_price_score(price):
                    maxscore = roul['价格']
                    return maxscore*(-exp(-0.01*price)+1)

                def get_key_score(text):
                    score = 0
                    for key in roul['优先关键字']:
                        if key in text:
                            score += roul['关键字']
                    for key in roul['排除关键字']:
                        if key in text:
                            score -= roul['关键字']
                    return score

                scorelist = [
                    get_shopname_score(iteminfo['shopname']),
                    get_price_score(iteminfo['price']),
                    get_amount_score(iteminfo['supplyCount']),
                    get_key_score(iteminfo['trialName']),
                ]

                # 数据添加
                iteminfo['scorelist'] = scorelist
                iteminfo['score'] = sum(scorelist)
                itemlist.append(iteminfo)
            # 显示进度 时间
            timelist.insert(0, time.time()-t)
            if len(timelist) > 10:
                timelist.pop()
            print('updateing...  {} %  {} min'.format(
                round(n*100/pageamount, 2), round(sum(timelist)/len(timelist)*(pageamount-n)/60, 2)))
            n += 1
        # 按照分数重新排序

        def sort_by_score(item):
            return item['score']
        itemlist.sort(key=sort_by_score, reverse=True)
        # 储存数据
        data = {
            'itemlist': itemlist,
            'updatetime': time.time(),
        }
        json.dump(data, open('data.json', 'w'),)
        print('Done! use {} s'.format(round(time.time()-t_start)))
        return data

    try:
        data = json.load(open('data.json'))
        if time.time()-data['updatetime'] > 12*60*60:
            raise TimeoutError

    except FileNotFoundError:
        print('Not find data file,Regeting...')
        data = reget()
    except TimeoutError:
        print('Data file timeout,Regeting...')
        #data = reget()
    except:
        print('unknow erro in loaddata! ')
    return data


if __name__ == '__main__':
    # load data
    itemlist = loaddata()['itemlist']

    # login
    driver = login()
  
    # clean follows
    if input('是否删除关注的店铺(y/n):') in ['y','']:
        delfollows(driver)
    # try items
    jdtry(driver, itemlist)
    # quite
    driver.quit()

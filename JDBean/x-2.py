import time
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


def login():
    def show_version():
        version = 'v-1.61'
        print('*************{}************'.format(version))
    show_version()
    try:
        driver = webdriver.Chrome('./chromedriver')
    except OSError:
        driver = webdriver.Chrome('./chromedriver.exe')

    size = 1000

    driver.set_window_size(size, size)
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

    print('Done!')
    return driver


def Resort_and_Save(shoplist):
    # 按照分数重新排序
    def sort_by_times(shop):
        return shop['times']
    shoplist.sort(key=sort_by_times, reverse=True)

    # 储存数据
    json.dump(shoplist, open('shoplist.json', 'w'),)
    return shoplist


def getshoplist():
    # shoplist = json.load(open('shoplist.json', 'r'))[10:20]

    t_start = time.time()
    # 载入数据
    try:
        shoplist = json.load(open('shoplist.json', 'r'))
    except FileNotFoundError:
        print('shop.json not find, using a default list=[] .')
        shoplist = []
    except:
        shoplist = []

    shopamount=len(shoplist)       
    if input('是否爬取数据(y/n):') == 'y':

        # get page number
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

        while n < pageamount:
            t1 = time.time()
            print('updateing...  {} %  {} min'.format(
                round(n*100/pageamount, 2), round(t*(pageamount-n)/60, 2)))
            # 获取 activity_id
            activity_id_list = []
            r = requests.get(
                'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n))
            r.raise_for_status
            listsoup = BeautifulSoup(r.text, 'html.parser')
            for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
                activity_id_list.append(li.attrs['activity_id'])
            # 通过 activity_id 获取 店铺信息
            for activity_id in activity_id_list:
                shopinfo = {}
                # 获取店铺信息
                url = 'https://try.jd.com/migrate/getActivityById?id={}'.format(
                    activity_id)
                try:
                    data = requests.get(url, timeout=10).json()['data']
                except:
                    print('error in get shop info')
                    continue

                # 检查 id 是不是已存在
                try:
                    idinlist = False
                    for shop in shoplist:
                        if shop['shopId'] == data['shopInfo']['shopId']:
                            idinlist = True
                            break
                except TypeError:
                    continue

                # 如果不在则提取数据 并且加入列表
                if not idinlist:
                    try:
                        shopinfo['shopId'] = data['shopInfo']['shopId']
                        shopinfo['shopname'] = data['shopInfo']['title']
                        shopinfo['times'] = 0
                        # 数据添加
                        shoplist.append(shopinfo)
                    except TypeError:
                        print('TypeError when get shop info ')
            t = time.time()-t1
            n += 1

        shoplist = Resort_and_Save(shoplist)
        #print('Done! use {} s  {} shops new add!'.format(round(time.time()-t_start),len(shoplist)-shopamount))
    return shoplist


def getbeans(shoplist, driver):
    n = 0
    l = len(shoplist)
    print('got {} shop!'.format(l))
    newshoplist = []
    for shop in shoplist:
        print('{}% ------- '.format(round(n*100/l, 2)), end='')
        shopid = shop['shopId']

        shopurl = 'https://mall.jd.com/index-{}.html'.format(shopid)
        driver.get(shopurl)
        try:
            btn = WebDriverWait(driver, 2.5).until(
                lambda d: d.find_element_by_css_selector("[class='J_drawGift d-btn']"))
            btn.click()
            # time.sleep(2)
            # fellowbtn=driver.find_element_by_class_name('jAttention')
            # fellowbtn.click()
            shop['times'] += 1
            print('Got it !')
        except TimeoutException:
            
            print('Bad luck')

    
        newshoplist.append(shop)
        n += 1
    Resort_and_Save(newshoplist)
    print('done!')
    driver.quit()


if __name__ == "__main__":
    shoplist =getshoplist()
    driver = login()
    getbeans(shoplist, driver)

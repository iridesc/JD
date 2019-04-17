from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException,NoSuchElementException
import reget
from math import exp, pi
import time
import requests
import re
from retry import retry
import random
import json
from reget import bar
datadir='./data/'



def login():
    def get_driver(headless=False,nopic=False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        if nopic:
            prefs = {"profile.managed_default_content_settings.images":2}
            chrome_options.add_experimental_option("prefs",prefs)
        try:
            driver = webdriver.Chrome(datadir+'chromedriver',options=chrome_options)
        except OSError:
            driver = webdriver.Chrome(datadir+'chromedriver.exe',options=chrome_options)
        except Exception as e:
            print(' error in {}  \n{}'.format('get_driver',str(e)))
            raise
    
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
     
    driver=get_driver(nopic=True,headless=True)
    driver.get('https://www.jd.com/')
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()

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
    except NoSuchElementException:
        pass
    except Exception as e:
            print(' error in {}  \n{}'.format('',str(e)))



def jdtry(driver, itemlist):

    @retry(tries=3, delay=2, backoff=2)
    def get_itempage_find_appbtn(driver,item):
        url = 'https://try.jd.com/{}.html'.format(item['activityid'])
        driver.get(url)
        return driver.find_element_by_class_name('app-btn')
    
    @retry(tries=3, delay=2, backoff=2)
    def get_dialogtext(app_btn,driver):
        app_btn.click()
        time.sleep(random.random()+1)
        dialog = driver.find_element_by_class_name(
            'ui-dialog-content')
        return dialog.text,dialog

    @retry(tries=3, delay=2, backoff=2)
    def click_fellow(dialog):
        dialog.find_element_by_class_name('y').click()
        time.sleep(random.random()*2+4)

    print('开始申请京东试用...')
    l=len(itemlist)
    n=0
    for item in itemlist:
        n=bar(n,l)
        # get itempage & find app-btn
        try:
           app_btn =get_itempage_find_appbtn(driver,item)
        except Exception as e:
            print(' error in {}  \n{}'.format('get itempage & find app-btn',str(e)))
            continue
    

        # check if have got
        if '查看更多' not in app_btn.text:
            # get dialogtext
            try:
                dialogtext,dialog = get_dialogtext(app_btn,driver)
            except Exception as e:
                print(' error in {}  \n{}'.format('get dialogtext',str(e)))
                continue
    
    
    

            # fenxi dialogtext
            if '超过上限' in dialogtext:
                print('Reach the maximum! Now break!')
                break
            
            elif '申请成功' in dialogtext:
                print('Success ! {}'.format(item['trialName']))
                time.sleep(random.random()*2+4)
            

            elif '需关注店铺' in dialogtext:
                try:
                    click_fellow(dialog)
                    print('Success ! {}'.format(item['trialName']))
                except Exception as e:
                    print(' error in {}  \n{}'.format('clickYES',str(e)))

            
            else:
                print(dialogtext)
        
        else:
            print('Have got befor!')
        
def jdbean(driver,beandata):
    print('开始获取京豆...')
    n = 0
    l = len(beandata)
    newbeandata = []
    for shop in beandata:
        n=bar(n,l)
        shopid = shop['shopId']
        shopurl = 'https://mall.jd.com/index-{}.html'.format(shopid)
        driver.get(shopurl)
        try:
            btn = WebDriverWait(driver, 2.5).until(
                lambda d: d.find_element_by_css_selector("[class='J_drawGift d-btn']"))
            btn.click()
            shop['times'] += 1
            print('Got it ! {}'.format(shop['shopname']))
        except TimeoutException:
            print('Bad luck {}'.format(shop['shopname']))
        except Exception as e:
            print(' error in {}  \n{}'.format('jdbean',str(e)))
            continue

        newbeandata.append(shop)
    json.dump(newbeandata,open(datadir+'Beandata.json', 'w'),ensure_ascii=False)

def loaddata():

    # 载入Beandata
    try:
        beandata = json.load(open(datadir+'Beandata.json', 'r'))
    except FileNotFoundError:
        print('Beandata not find, using a default list as [] .')
        beandata = []
    except Exception as e:
            print(' error in {}  \n{}'.format('load Beandata',str(e)))
            raise

    # 载入Trydata
    try:
        Trydata = json.load(open(datadir+'Trydata.json'))
        trydata=Trydata['trydata']
        if time.time()-Trydata['updatetime'] > 12*60*60:
            raise TimeoutError

    except (FileNotFoundError,TimeoutError):
        print('Not find data file or file timeout,Regeting...')
        trydata,beandata = reget.Main()
    except Exception as e:
            print(' error in {}  \n{}'.format('loaddata',str(e)))
            raise
    
  
    print('\ntrydata: {}\nbeandata: {}\n'.format(len(trydata),len(beandata)))
    return trydata,beandata


if __name__ == '__main__':

    # login
    driver = login()
  
    # clean follows
    if input('是否删除关注的店铺(y/n):') in ['y','']:
        delfollows(driver)
    
    # load data
    trydata,beaandata = loaddata()
    
    # try items
    jdtry(driver,trydata)

    # get bean
    jdbean(driver,beaandata)


    # quite
    driver.quit()

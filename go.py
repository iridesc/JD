from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException,NoSuchElementException
from reget import reget
from reget import bar
from reget import estimate
import time
from retry import retry
import random
import json
import sys

import requests


TEST=False
max_clean_n = 20
EachRequestShopAmount=50
EachUpdateShopAmount=5
BeanDataRecent=14
ServerAddr='http://0.0.0.0/api/'
TryDataGap=1
DriverCleanN=0

def get_driver(headless=True,nopic=True,nostyle=True):
    systemtype=sys.platform
    fireFoxOptions = webdriver.FirefoxOptions()
    firefox_profile = webdriver.FirefoxProfile()

    if not TEST:   
        if headless:
            # 无头模式
            fireFoxOptions .add_argument("--headless")
        if nopic:
            #不加载图片
            firefox_profile.set_preference("permissions.default.image",2)  
        if nostyle:
            #禁用样式表文件
            firefox_profile.set_preference("permissions.default.stylesheet",2)  
    #更新设置
    firefox_profile.update_preferences()  
    # 系统判断
    if systemtype=='linux':
        executable_path='./data/geckodriver'
    elif systemtype=='win32':
        executable_path='./data/geckodriver.exe'
    else:
        print('不支持的系统类型！')
        raise OSError
    driver = webdriver.Firefox(executable_path=executable_path,firefox_profile=firefox_profile,options=fireFoxOptions,service_log_path='./data/geckodriver.log')

    # 设置最长加载时间
    # driver.set_page_load_timeout(30)
    return driver

def clean_driver(driver):
    
    @retry(tries=15, delay=1, backoff=2)
    def get_page(driver):
        driver.get('https://www.jd.com/')
        return driver
    
    global DriverCleanN
    
    if DriverCleanN % max_clean_n == 0:
        print('cleaning driver...')
        cookies=driver.get_cookies()
        driver.quit()
        driver=get_driver()
        driver=get_page(driver)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                if TEST:
                    print(e)
                    print(cookie)

        DriverCleanN=1
        print('Done .')
    else:
        DriverCleanN+=1
    return driver

def login():
    def get_one_user():
        try:
            userlist=json.load(open('./data/users.json'))
            l=len(userlist)
          
            if l==0:
                user = None
            elif l==1:
                user=userlist[0]
            else:
                print('找到{}个user'.format(l))
                n=1
                for user in userlist:
                    print('{}--{}'.format(n,user['username']))
                    n+=1

                while True:
                    try:
                        user=userlist[int(input('输入user编号:'))-1]
                        break
                    except:
                        print('输入错误，重新输入')

        except (FileNotFoundError,IndexError):
            user=None
            userlist=[]
        except Exception as e:
         
            print('error in {} .\n{}'.format('get_one_user',str(e)))
            user=None
        
        json.dump(userlist,open('./data/users.json','w'),ensure_ascii=False,indent=2)
        return user

    def save_one_user(user):
        username=user['username']

        # 检查文件 如果user存在则删除 
        users=json.load(open('./data/users.json'))
        newusers=[]
        for olduser in users:
            if olduser['username'] != user['username']:
                newusers.append(olduser)
        # 重新添加
        newusers.append(user)
        json.dump(newusers,open('./data/users.json','w'),ensure_ascii=False,indent=2)
     
    def test_user_cookies_status(user,driver):
        print('testing {} ...'.format(user['username']))
        testurl='https://home.jd.com/'
        url='https://jd.com/'
        driver.get(url)
        for cookie in user['cookies']:
            driver.add_cookie(cookie)
        driver.get(testurl)
        current_url=driver.current_url
        if 'passport.jd.com' in current_url:
            logined=False
        elif 'home.jd.com' in current_url:
            logined=True
            
        else:
            print('unknow user login status !!!!!')
            print(current_url)
            logined=False
        return logined,driver

    def relogin(driver,userid=None,password=None):
        print('login...')
        driver.quit()
        driver=get_driver(headless=False,nopic=False,nostyle=False)
        driver.set_window_size(350,350)
        driver.get('https://passport.jd.com/new/login.aspx')
       
        # 转到账户密码登录
        driver.find_element_by_class_name('login-tab-r').click()
        
        while not driver.current_url == 'https://www.jd.com/':
            userid_box=driver.find_element_by_id('loginname')
            password_box=driver.find_element_by_id('nloginpwd')
            # 清空输入框    
            userid_box.clear()
            password_box.clear()
            
            # 获取账户密码
            if userid== None or password == None:
                userid=input('输入登录ID：')    
                password=input('输入登录密码：')

            password_box.send_keys(password)
            userid_box.send_keys(userid)

            driver.find_element_by_id('loginsubmit').click()
            WebDriverWait(driver,10).until(lambda driver:driver.find_element_by_xpath('/html/body/div[4]/div/div').is_displayed())
            print('滑动以通过验证...')
            WebDriverWait(driver,120).until_not(lambda driver:driver.find_element_by_xpath('/html/body/div[4]/div/div').is_displayed())
            
            # 如果出现错误 打印出信息
            try:
                msg=driver.find_element_by_class_name('msg-error')
                if msg.is_displayed():
                    userid = None 
                    password = None
                    print(msg.text)
            except: 
                pass

        # 组建出该user
        cookies=driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] =='unick':
                    username=cookie['value']
                    break
        user={
            'username':username,
            'userid':userid,
            'password':password,
            'cookies':cookies,
        }
        return driver,user
    
   
    an=input('y:载入userlist，n:添加新user\n>>>')
    driver=get_driver()
    if an=='' or an == 'y':
        user=get_one_user()
        if user != None:
            logined,driver=test_user_cookies_status(user,driver)
            if  logined:
                user['cookies']=driver.get_cookies()
            else:
                print('{} not login !'.format(user['username']))
                driver,user = relogin(driver,password=user['password'],userid=user['userid'])
        else:
            print('not find any user! please let someone login !') 
            driver,user= relogin(driver)
    else:
        print('new user login ....')
        driver,user=relogin(driver)    
    
    
    save_one_user(user=user)

    driver.quit()           
    driver=get_driver()
    driver.get('https://www.jd.com/')
    for cookie in user['cookies']:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            if TEST:
                print(e)
                print(cookie)
    driver.refresh()
    print('\nHello {}\n'.format(user['username']))
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
            return driver
    except Exception as e:
            print(' error in {}  \n{}'.format('',str(e)))

def jdtry(driver):

    @retry(tries=6, delay=1, backoff=2)
    def get_itempage_find_appbtn(driver,item):
        url = 'https://try.jd.com/{}.html'.format(item['ActivityId'])
        driver.get(url)
        btn=driver.find_element_by_class_name('app-btn')
        return btn
    
    @retry(tries=3, delay=1, backoff=2)
    def get_dialogtext(app_btn,driver):
        app_btn.click()
        time.sleep(random.random()+1)
        dialog = driver.find_element_by_class_name(
            'ui-dialog-content')
        return dialog.text,dialog

    @retry(tries=3, delay=1, backoff=2)
    def click_fellow(dialog):
        dialog.find_element_by_class_name('y').click()
        time.sleep(random.random()*2+4)
    
    @retry(tries=3, delay=1, backoff=2)
    def GetTryData(TryDataGap):
        send_data={
        'Reason':'GetTryData',
        'Days':1,
        }

        r=requests.post(ServerAddr,json=send_data)
        print(r.status_code)
        r.raise_for_status
        data=r.json()
        return data



    global DriverCleanN
    print('获取试用列表...')
    data=GetTryData(TryDataGap)
    if not data['Status']:
        if data['Reason']=='TryDataTimeout':
            print(data['Reason'])
            try_activity_list=reget()
        else:
            print(data)
            raise Exception
    else:
        try_activity_list=estimate(data['TryActivityList'])

    print('开始申请京东试用...')
 
    n=0
    
    l=len(try_activity_list)
    for try_activity in try_activity_list:
        n=bar(n,l)
        # get itempage & find app-btn
        try:
            app_btn =get_itempage_find_appbtn(driver,try_activity)
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
                print('Success ! {}'.format(try_activity['TrialName']))
                time.sleep(random.random()*2+4)
            

            elif '需关注店铺' in dialogtext:
                try:
                    click_fellow(dialog)
                    print('Success ! {}'.format(try_activity['TrialName']))
                except Exception as e:
                    print(' error in {}  \n{}'.format('clickYES',str(e)))
            else:
                print('infomation:',dialogtext)
        else:
            print('Have got befor!')
        
        driver= clean_driver(driver)

    return driver
        
def jdbean(driver):
    @retry(tries=3, delay=1, backoff=2)
    def get_shop_page(shop_id,driver):
        shopurl = 'https://mall.jd.com/index-{}.html'.format(shop_id)
        driver.get(shopurl)
        return driver

    @retry(tries=3, delay=1, backoff=2)
    def GetBeanData(BeanDataRecent):

        send_data={
            'Reason':'GetBeanData',
            'Days':BeanDataRecent,
        }

        r=requests.post(ServerAddr,json=send_data)
        print(r.status_code)
        r.raise_for_status
        data=r.json()
        if not data['Status']:
            print(data)

        if BeanDataRecent != 0:
            BeanDataRecent=0

        return data['ShopList'],BeanDataRecent
    
    @retry(tries=3, delay=1, backoff=2)
    def UpdateBeanData(shop_list_for_update):
        if len(shop_list_for_update)>= EachUpdateShopAmount:
            send_data={
                'Reason':'UpdateBeanData',
                'ShopList':shop_list_for_update
            }
            r=requests.post(ServerAddr,json=send_data)
            print(r.status_code)
            r.raise_for_status
            data=r.json()
            if data['Status']:
                shop_list_for_update=[]
            else:
                print(data)

        return shop_list_for_update     

    global DriverCleanN


    print('开始获取京豆...')

    # 用于预存要更新的Shop
    shop_list_for_update=[]
    BeanDataRecent=globals()['BeanDataRecent']
    while True:
        # 获取一组店铺
        try:
            
            shop_list,BeanDataRecent=GetBeanData(BeanDataRecent=BeanDataRecent)
        except Exception as e:
            print('error in {} .\n{}'.format('GetBeanData',str(e)))
            continue
        
        DriverCleanN=1
        for shop in shop_list:

            # 进入店铺主页
            try:
                driver=get_shop_page(shop['ShopId'],driver)
            except Exception as e:
                print('error in {} .\n{}'.format('get_shop_page',str(e)))
                continue
            
            # 等待获取优惠
            try:
                btn = WebDriverWait(driver, 2).until(
                    lambda d: d.find_element_by_css_selector("[class='J_drawGift d-btn']"))
                btn.click()
                print('Got it ! {}'.format(shop['ShopName']))
                shop['LastGotTime']=time.time()
                shop_list_for_update.append(shop)

            except TimeoutException:

                print('Bad luck {}'.format(shop['ShopName']))
            
            except Exception as e:
                print(' error in {}  \n{}'.format('jdbean',str(e)))
            
            # 重置浏览器
            driver = clean_driver(driver)
            
            # 发送要更新的店铺数据
            try:
                shop_list_for_update=UpdateBeanData(shop_list_for_update)
            except Exception as e:
                  print('error in {} .\n{}'.format('UpdateBeanData',str(e)))
                
    return driver


if __name__ == '__main__':
    try:
        # login
        driver = login()
    
        # clean follows
        if input('是否删除关注的店铺(y/n):') in ['y','']:
            driver=delfollows(driver)
        
        # try items
        # driver=jdtry(driver)

        # get bean
        driver=jdbean(driver)

        # quite
        driver.quit()

    except Exception as e:            
      
        print('a fatal error！now quit！')
        print(e)
        
        # quite
        driver.quit()
        raise

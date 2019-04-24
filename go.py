from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException,NoSuchElementException
import reget
import time
from retry import retry
import random
import json
import sys
from reget import bar



TEST=False
max_clean_n = 20

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



def clean_driver(driver,clear_n):
    
    @retry(tries=15, delay=1, backoff=2)
    def get_page(driver):
        driver.get('https://www.jd.com/')
        return driver
    
    if clear_n % max_clean_n == 0:
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

        clear_n=1
        print('Done .')
    else:
        clear_n+=1
    return driver,clear_n

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
            print('unknow error in get_one_user')
            print(str(e))
            user=None
        
        json.dump(userlist,open('./data/users.json','w'),ensure_ascii=False,indent=2)
        return user

    def save_one_user(user):
        username=user['username']
      
        # 检查文件 如果user存在则删除 
        users=json.load(open('./data/users.json'))
        newusers=[]
        for olduser in users:
            if username != user['username']:
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
                userpassword=input('输入登录密码：')

            password_box.send_keys(userpassword)
            userid_box.send_keys(userid)

            driver.find_element_by_id('loginsubmit').click()
            WebDriverWait(driver,10).until(lambda driver:driver.find_element_by_xpath('/html/body/div[4]/div/div').is_displayed())
            print('滑动以通过验证...')
            WebDriverWait(driver,120).until_not(lambda driver:driver.find_element_by_xpath('/html/body/div[4]/div/div').is_displayed())
            
            # 如果出现错误 打印出信息
            try:
                msg=driver.find_element_by_class_name('msg-error')
                if msg.is_displayed():
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
            'cookies':cookies,
            'userid':userid,
            'password':password,
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

def jdtry(driver, itemlist):

    @retry(tries=6, delay=1, backoff=2)
    def get_itempage_find_appbtn(driver,item):
        url = 'https://try.jd.com/{}.html'.format(item['activityid'])
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
    
    print('开始申请京东试用...')
 
    
    n=0
    clear_n=1
    l=len(itemlist)
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
                print('infomation:',dialogtext)
        else:
            print('Have got befor!')
        
        driver,clear_n = clean_driver(driver,clear_n)

    return driver
        
def jdbean(driver,beandata):
    @retry(tries=3, delay=1, backoff=2)
    def get_shop_page(shuoid,driver):
        shopurl = 'https://mall.jd.com/index-{}.html'.format(shopid)
        driver.get(shopurl)
        return driver


    print('开始获取京豆...')

    n = 0
    clear_n=1
    l = len(beandata)
    newbeandata = {}
    for shop in beandata:
        shopid = shop['shopId']
        # print('shopId:',shopid)

        n=bar(n,l)
      
        try:
            driver=get_shop_page(shopid,driver)
        except Exception as e:
            print('error in {} .\n{}'.format('get_shop_page',str(e)))
            continue
        
        try:
            btn = WebDriverWait(driver, 2.5).until(
                lambda d: d.find_element_by_css_selector("[class='J_drawGift d-btn']"))
            btn.click()
            shop['score'] = 0
            print('Got it ! {}'.format(shop['shopname']))
        except TimeoutException:
            print('Bad luck {}'.format(shop['shopname']))
            shop['score']-=1
            
        except Exception as e:
            print(' error in {}  \n{}'.format('jdbean',str(e)))
            continue
        
        newbeandata[shop['shopId']]=shop
    
        driver,clear_n = clean_driver(driver,clear_n)

    json.dump(newbeandata,open('./data/Beandata.json', 'w'),ensure_ascii=False)
    return driver

def loaddata():
    # 对beandata进行排序的函数
    def sort_Bean(shop):
        return shop['score']

    # 载入Trydata
    try:
        Trydata = json.load(open('./data/Trydata.json'))
        trydata=Trydata['trydata']
        if time.time()-Trydata['updatetime'] > 12*60*60:
            raise TimeoutError
        else:
            # Trydata载入成功则载入Beandata
            try:
                beandata = json.load(open('./data/Beandata.json'))
                beandata = [shop[1] for shop in beandata.items()]
                beandata.sort(key=sort_Bean,reverse=True)
            except FileNotFoundError:
                print('Beandata not find, using a default list as [] .')
                beandata = []
            except Exception as e:
                    print(' error in {}  \n{}'.format('load Beandata',str(e)))
                    raise

    except (FileNotFoundError,TimeoutError):
        print('Not find data file or file timeout,Regeting...')
        trydata,beandata = reget.Main()
        beandata = [shop[1] for shop in beandata.items()]
        beandata.sort(key=sort_Bean,reverse=True)
    except Exception as e:
            print(' error in {}  \n{}'.format('loaddata',str(e)))

    print('\ntrydata: {}\nbeandata: {}\n'.format(len(trydata),len(beandata)))
    return trydata,beandata


if __name__ == '__main__':
    try:
        # login
        driver = login()
    
        # clean follows
        if input('是否删除关注的店铺(y/n):') in ['y','']:
            driver=delfollows(driver)
        
        # load data
        trydata,beaandata = loaddata()
        
        # try items
        driver=jdtry(driver,trydata)

        # get bean
        driver=jdbean(driver,beaandata)

        # quite
        driver.quit()

    except Exception as e:            
        # quite
        print('a fatal error！now quit！')
        print(e)
        driver.quit()

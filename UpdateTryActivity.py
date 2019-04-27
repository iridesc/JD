import requests
from bs4 import BeautifulSoup
import time
import json

from retry import retry


ServerAddr='http://111.231.78.78:1231/api/'
# ServerAddr='http://0.0.0.0:80/api/'

def bar(n,l,long=50,done='=',head='>',blank='.'):
    print('[{}]{}%'.format((int(n/l*long)*done+head+blank*long)[0:long],round(n/l*100,2),))
    return n+1

def GetPageAmount():
    @retry(tries=3, delay=1, backoff=2)
    def getpageamount():
        r = requests.get('https://try.jd.com/activity/getActivityList',timeout=10)
        r.raise_for_status
        listsoup = BeautifulSoup(r.text, 'html.parser')
        pageamount = int(listsoup.find_all(
            'span', {'class': 'fp-text'})[0].i.text)+1

        return pageamount
    
    print('更新试用数据 ...',end=' ')
    try:
        pageamount=getpageamount()
    except Exception as e:
            print(' in {} .\n{}'.format('getpageamount',str(e)))
            raise Exception
    print(pageamount)
    print('Done .')
    return pageamount

def getActivityIdList(pageamount):
    @retry(tries=3, delay=1, backoff=2)
    def getListPageText(n):

        r = requests.get(
            'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n),timeout=10)
        return r.text
    
    @retry(tries=3, delay=1, backoff=2)
    def RemoveExistingActivityId(activity_id_list):
        print('去除服务端已存在的ID ...' ,end=' ')
        send_data={
        'Reason':'RemoveExistingActivityId',
        'ActivityIdList':activity_id_list,
        }
        r=requests.post(ServerAddr,json=send_data)
        r.raise_for_status
        data=r.json()
        print(len(activity_id_list),' -> ',len(data['ActivityIdList']))
        print('Done .')
        return data['ActivityIdList']
    
    print('获取需要抓活动ID列表 ...')
    n = 1
    all_activity_id_list = []
    while n < pageamount:
        n=bar(n,pageamount)
        # 获取 activity_id
        try:
            text=getListPageText(n)
        except Exception as e:
            print('error in {} .\n{}'.format('getListPageText',str(e)))
            continue
        listsoup = BeautifulSoup(text, 'html.parser')
        for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
            # 只获取24h内可以结束的
            #if (int(li.attrs['end_time'])/1000-time.time())/(60*60) < 24:
            all_activity_id_list.append(li.attrs['activity_id'])
    
    # 消除服务端已保存的的
    try:
        need_check_activity_id_list=RemoveExistingActivityId(all_activity_id_list)
    except Exception as e:
        need_check_activity_id_list = all_activity_id_list
        print('error in {} .\n{}'.format('RemoveExistingActivityId',str(e)))
      
    
    return need_check_activity_id_list

def getattrs(activity_id_list):

    @retry(tries=3, delay=1, backoff=2)
    def get_activity_data(activity_id):
        url='https://try.jd.com/migrate/getActivityById?id={}'.format(activity_id)
        r = requests.get(url,timeout=10).json()
        data = r['data']
        return data
      
    @retry(tries=3, delay=1, backoff=2)
    def get_price(iteminfo):
        r=requests.get(
                'https://p.3.cn/prices/mgets?skuIds=J_{}'.format(iteminfo['TrialSkuId']),timeout=10)
        # print(r.status_code)
        j=r.json()
        return j[0]['p']



    
    print('获取活动详情 ...')
    trydata=[]
    n=0
    l=len(activity_id_list)
    for activity_id in activity_id_list:
        n=bar(n,l)
        iteminfo = {}
    
        # 获取各种属性
        try:
            data=get_activity_data(activity_id)
        except Exception as e:
            print('error in {} .\n{}'.format('get_activity_data',str(e)))
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
            iteminfo['ShopId'] = ''

        # 获取价格
        try:
            price = get_price(iteminfo)
        except Exception as e:
            print('error in {} .\n{}'.format('get_price',str(e)))
            price = 25
        iteminfo['Price'] = float(price)

        trydata.append(iteminfo)
    
    return trydata

def UpdateTryData(try_activity_list):

    @retry(tries=5, delay=1, backoff=2)    
    def updatetrydata(try_activity_list):
        send_data={

            'Reason':'UpdateTryData'
        }

        send_data['TryActivityList']=try_activity_list
        r=requests.post(ServerAddr,json=send_data)
        # print(r.status_code)
        r.raise_for_status
        data=r.json()
        return data
    print('上传活动数据 ...')
    try:
        updatetrydata(try_activity_list)
    except Exception as e:
        print(' in {} .\n{}'.format('UpdateTryData',str(e)))
    print('Done .')

def UpdateTryActivity():

    # 获取页数
    pageamount=GetPageAmount()

    # 获取 activity_id_list
    need_check_activity_id_list = getActivityIdList(pageamount)
 

    # 获取活动信息
    try_activity_list= getattrs(need_check_activity_id_list)

    # 上传
    
    UpdateTryData(try_activity_list)
import requests
from bs4 import BeautifulSoup
import time
import json
from math import exp,pi
from retry import retry


ServerAddr='http://111.231.78.78:2580/api/'
#ServerAddr='http://0.0.0.0:80/api/'

def bar(n,l,long=50,done='=',head='>',blank='.'):
    print('[{}]{}%'.format((int(n/l*long)*done+head+blank*long)[0:long],round(n/l*100,2),))
    return n+1

@retry(tries=3, delay=1, backoff=2)
def getpageamount():
    r = requests.get('https://try.jd.com/activity/getActivityList',timeout=10)
    r.raise_for_status
    listsoup = BeautifulSoup(r.text, 'html.parser')
    pageamount = int(listsoup.find_all(
        'span', {'class': 'fp-text'})[0].i.text)+1

    return pageamount

def getActivityIdList(pageamount):

    @retry(tries=3, delay=1, backoff=2)
    def getListPageText(n):

        r = requests.get(
            'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n),timeout=10)
        return r.text

    print('获取试用列表')
    n = 1
    activity_id_list = []
    while n < pageamount:
        n=bar(n,pageamount)
        # 获取 activity_id
       
        try:
            text=getListPageText(n)
        except Exception as e:
            print(' in {} .\n{}'.format('getListPageText',str(e)))
            continue
        listsoup = BeautifulSoup(text, 'html.parser')
        for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
            # 只获取24h内可以结束的
            #if (int(li.attrs['end_time'])/1000-time.time())/(60*60) < 24:
            activity_id_list.append(li.attrs['activity_id'])
    return activity_id_list

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



    
    print('获取试用详情')
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
                iteminfo['activityid']))
            iteminfo['Shopname'] = ''
            iteminfo['ShopId'] = ''

        # 获取价格
        try:
            price = get_price(iteminfo)
        except Exception as e:
            print(' in {} .\n{}'.format('get_price',str(e)))
            price = 25
        iteminfo['Price'] = float(price)

        trydata.append(iteminfo)
        
    return trydata

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
                '关键字': 20,
                '优先关键字': ['鼠标', '键盘', '硬盘', '内存', '显卡', '笔记本', '中性笔', '路由器', '智能', 'u盘', '耳机', '音箱', '储存卡'],
                '排除关键字': ['丝袜', '文胸', '舞鞋','课程', '流量卡', '婴儿', '手机壳','钢化膜', '润滑油', '纸尿裤','白酒', '药', '保健品'],
            }
            json.dump(rule, open('./data/rule.txt', 'w'),ensure_ascii=False,indent=4)

            print('can\'t find rule.txt, useing default rule !')
        return rule


    # 载入规则
    rule=loadrule()

    data=[]
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
                    score += rule['关键字']
            for key in rule['排除关键字']:
                if key in text:
                    score -= rule['关键字']
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


@retry(tries=3, delay=1, backoff=2)
def UpdateTryData(try_activity_list):
    send_data={

        'Reason':'UpdateTryData'
    }

    send_data['TryActivityList']=try_activity_list
    r=requests.post(ServerAddr,json=send_data)
    print(r.status_code)
    r.raise_for_status
    data=r.json()
    return data


def reget():

    # 获取页数
    try:
        pageamount=getpageamount()
    except Exception as e:
            print(' in {} .\n{}'.format('getpageamount',str(e)))
            raise Exception
    

    # 获取 activity_id_list
    activity_id_list = getActivityIdList(pageamount)
 

    # 获取信息
    try_activity_list= getattrs(activity_id_list)

    # 上传
    try:
        UpdateTryData(try_activity_list)
    except Exception as e:
        print('try_activity_list 上传失败！\n',str(e))
    

    # 评估 与 排序
    try_activity_list=estimate(try_activity_list)


    return try_activity_list
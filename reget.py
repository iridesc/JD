import requests
from bs4 import BeautifulSoup
import time
import json
from math import exp,pi
from retry import retry

datadir='./data/'

def bar(n,l,long=50,done='=',head='>',blank='.'):
    print('[{}]{}%'.format((int(n/l*long)*done+head+blank*long)[0:long],round(n/l*100,2),))
    return n+1

@retry(tries=3, delay=1, backoff=2)
def getpageamount():
    r = requests.get('https://try.jd.com/activity/getActivityList')
    r.raise_for_status
    listsoup = BeautifulSoup(r.text, 'html.parser')
    pageamount = int(listsoup.find_all(
        'span', {'class': 'fp-text'})[0].i.text)+1

    return pageamount

def getActivityIdList(pageamount):

    @retry(tries=3, delay=1, backoff=2)
    def getListPageText(n):
        r = requests.get(
            'https://try.jd.com/activity/getActivityList?page={}&activityState=0'.format(n))
        return r.text

    print('获取试用列表')
    n = 1
    while n < pageamount:
        n=bar(n,pageamount)
        # 获取 activity_id
        activity_id_list = []
        try:
            text=getListPageText(n)
        except Exception as e:
            print(' in {} .\n{}'.format('getListPageText',str(e)))
            continue
        listsoup = BeautifulSoup(text, 'html.parser')
        for li in listsoup.find('div', {'class': 'con'}).find_all('li'):
            # 只获取24h内可以结束的
            if (int(li.attrs['end_time'])/1000-time.time())/(60*60) < 24:
                activity_id_list.append(li.attrs['activity_id'])
    return activity_id_list

def getattrs(activity_id_list):

    @retry(tries=3, delay=1, backoff=2)
    def get_activity_data(activity_id):
        url='https://try.jd.com/migrate/getActivityById?id={}'.format(activity_id)
        r = requests.get(url).json()
        data = r['data']
        return data
      
    @retry(tries=3, delay=1, backoff=2)
    def get_price(iteminfo):
        return requests.get(
                'https://p.3.cn/prices/mgets?skuIds=J_{}'.format(iteminfo['trialSkuId'])).json()[0]['p']

    print('获取试用详情')
    trydata=[]
    # 载入Beandata
    try:
        beandata = json.load(open(datadir+'Beandata.json', 'r'))
    except FileNotFoundError:
        print('Beandata not find, using a default list as [] .')
        beandata = []
    except:
        print('unknow  in load Beandata! ')
        beandata = []
    
    n=0
    l=len(activity_id_list)
    for activity_id in activity_id_list:
        n=bar(n,l)
        iteminfo = {}
        shopinfo = {}
    
        # 获取各种属性
        try:
            data=get_activity_data(activity_id)
        except Exception as e:
            print(' in {} .\n{}'.format('get_activity_data',str(e)))
            continue
    
        # 检查 店铺id 是不是已存在 不存在则加入
        try:
            idinlist = False
            for shop in beandata:
                if shop['shopId'] == data['shopInfo']['shopId']:
                    idinlist = True
                    break
            if not idinlist:
                shopinfo['shopId'] = data['shopInfo']['shopId']
                shopinfo['shopname'] = data['shopInfo']['title']
                shopinfo['times'] = 0
                # 数据添加
                beandata.append(shopinfo)
        except TypeError:
            print('TypeError when get shop info ')

        # 活动属性提取
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
            iteminfo['shopId'] = ''

        # 获取价格
        try:
            price = get_price(iteminfo)
        except Exception as e:
            print(' in {} .\n{}'.format('get_price',str(e)))
            price = 25
    
        iteminfo['price'] = float(price)

        trydata.append(iteminfo)
    return trydata,beandata

def loadrule():
    try:
            rule = json.load(open(datadir+'rule.txt'))
    except:
        rule = {
            '自营': 30,
            '旗舰': 15,
            '价格': 30,
            '数量': 30,
            '关键字': 20,
            '优先关键字': ['鼠标', '键盘', '硬盘', '内存', '显卡', '笔记本', '中性笔', '路由器', '智能', 'u盘', '耳机', '音箱', '储存卡'],
            '排除关键字': ['丝袜', '文胸', '课程', '流量卡', '婴儿', '手机壳', '润滑油', '纸尿裤', '药', '保健品'],
        }
        json.dump(rule, open(datadir+'rule.txt', 'w'),ensure_ascii=False,indent=4)

        print('can\'t find rule.txt, useing default rule !')
    return rule

def estimate(rule,trydata):
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
            get_shopname_score(iteminfo['shopname']),
            get_price_score(iteminfo['price']),
            get_amount_score(iteminfo['supplyCount']),
            get_key_score(iteminfo['trialName']),
        ]

        # 数据添加
        iteminfo['scorelist'] = scorelist
        iteminfo['score'] = sum(scorelist)
        data.append(iteminfo)
    return data

def Main():

    # 获取页数
    try:
        pageamount=getpageamount()
    except Exception as e:
            print(' in {} .\n{}'.format('getpageamount',str(e)))

    # 获取 activity_id_list
    activity_id_list = getActivityIdList(pageamount)
 

    # 获取信息
    trydata,beandata = getattrs(activity_id_list)

    # 载入规则
    rule=loadrule()

    # 评估
    trydata=estimate(rule,trydata)


    # 按照分数重新排序
    def sort_by_score(item):
        return item['score']
    trydata.sort(key=sort_by_score, reverse=True)


    # 储存数据
    Trydata={
        'updatetime':time.time(),
        'trydata':trydata,
    }

    json.dump(Trydata, open(datadir+'Trydata.json', 'w'),ensure_ascii=False)
    json.dump(beandata,open(datadir+'Beandata.json', 'w'),ensure_ascii=False)

    return trydata,beandata



import requests,time,json
try:
    shopidlist = json.load(open('shopidlist.json'))
except:
    shopidlist = []

print(len(shopidlist))

with open('n.txt',) as target:
N = int(target.read())


gap=1

for n in range(N,20000):
    url = 'https://mall.jd.com/index-{}.html'.format(n)
    r=requests.get(url)
    text=r.text
    print(url)
    try:
        if '抱歉!' in text:
            print('页面失联')
      
          
        elif '<!-- JSHOP店铺页面内容 -->' in text:
            print('找到店铺')
            shopidlist.append(n)
    
        else:    
            print('new type')
            with open('x.html','w') as f:
                f.write(text)
            break
    except:
        pass

json.dump(shopidlist,open('shopidlist.json', 'w'))
with open('n.txt','w') as target:
    target.write(str(n))
    pass
 

import random,time
from math import exp,pi
import matplotlib.pyplot as plt
import numpy as np
import json,requests
from bs4 import BeautifulSoup
import os

os.getcwd




# 'https://p.3.cn/prices/mgets?skuIds=J_'

# r=requests.get('https://try.jd.com/547044.html')
# with open('item.html','w') as target:
#     target.write(r.text)
#     pass
# pagesoup = BeautifulSoup(r.text, 'html.parser')
# itemname=pagesoup.find(attrs={'class':'info'}).div.text
# print(itemname)
# def get_price_score(x):
#     maxscore=20
#     return maxscore*(-exp(-0.01*x)+1)








# def get_amount_score(x):
#     E = 10  # excpection
#     theta = 50
#     maxscore = 35
#     fix = exp(-(10-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5)
#     return (exp(-(x-E)**2/(2*theta**2)) / (theta*(2*pi)**0.5))*maxscore/fix


# def get_time_score(x):
#                 maxscore=10
#                 k=0.0000004
#                 return -k*x+maxscore



# y=[get_price_score(i) for i in range(1,5000)]
# x = list(range(1, 5000))

# plt.plot(x, y, 'g.')
# plt.show()

# y = [get_amount_score(i) for i in range(0, 200)]
# x = list(range(0, 200))
# n = 0
# while n < len(x):
#     print(x[n], '  ', y[n])
#     n += 1

# y = [int(i) for i in json.load(open('shopid.json'))]
# mid = (max(y)+min(y))/2
# y1=[]
# y2=[]
# for i in y:
#     if i>mid:
#         y1.append(i)
#     else:
#         y2.append(i)
# print(max(y1),'  ',min(y1))
# print(max(y2), '  ', min(y2))
# y1.sort()
# y2.sort()

# x=list(range(len(y)))

# x1 = list(range(len(y1)))

# x2 = list(range(len(y2)))

# plt.plot(x1, y1, 'g.')
# plt.show()
# plt.plot(x2, y2, 'g.')
# plt.show()

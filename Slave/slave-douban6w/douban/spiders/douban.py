#!/usr/local/bin/python
#-*- encoding:utf-8 -*-

import json, unirest
from scrapy.spiders import Spider,Rule
from scrapy.selector import Selector
from scrapy.linkextractors import LinkExtractor as sle
from collections import OrderedDict
import logging

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.conf import settings
#!< 插入unvisitedurls
# curl -X PUT -H 'Content-Type: application/json'
# -d '{"urls": [{"url":"http://book.douban.com/isbn/9787530214695", "spider":"douban"}]}'
# http://192.168.100.3:5000/unvisitedurls

#!< 运行spider
# douban6w
# scrapy crawl douban -a url='http://192.168.100.3:5000/unvisitedurls?start=0&offset=10&spider=6w'

class DoubanISBN(Spider):
    #!< DOT name
    name = "douban"
    allowed_domains = ["douban.com"]

    handle_httpstatus_list = [\
    400, 401, 402, 403, 404, 405, 406, 407, 408, 409,\
    410, 411, 412, 413, 414, 415, 416, 417, 418, 419,\
    420, 421, 422, 423, 424, 426, 428, 429, 431,\
    440, 444, 449,\
    450, 451,\
    494, 495, 496, 496, 497, 498, 499,\
    500, 501, 502, 503, 504, 505, 506, 507, 508, 509,\
    510, 511,\
    520, 522,\
    598, 599\
    ]

    #!< load isbns file.
    def __init__(self, url=None):

        #print "here i am"
        if url:
            # retrieve with post method, put for create, get for read, delete for delete
            # unvisitedurls http://localhost:5000/unvisitedurls?start=0&offset=10&spider=6w
            unirest.timeout(180)
            req = unirest.post(url, headers={"Accept":"application/json"})
            self.start_urls = [data['url'] for data in req.body['data']]
            self.name = url[url.find('spider=')+7:]

            self.visitedurldict = OrderedDict()
            self.datadict       = OrderedDict()
            self.filedict       = OrderedDict()
            self.deadurldict    = OrderedDict()

            self.visitedurldict['urls'] = []
            self.datadict['datas']      = []
            self.filedict['files']      = []
            self.deadurldict['urls']    = []

            rules = (
                Rule(sle(allow=("http://book.douban.com/isbn/\d+$")), callback="parse", follow=True),
                Rule(sle(allow=("http://book.douban.com/subject/\d+$")), callback="parse", follow=True),
            )
        # def __del__(self) work
        dispatcher.connect(self.spider_closed, signals.spider_closed)


    #!< 单独处理每一本书籍信息
    def parse(self, response):

        sel = Selector(text=response.body)

        # OrderedDict的Key会按照插入的顺序排列
        orderdict = OrderedDict()

        #!< 书名，书籍封面URL，评分
        title  = sel.xpath('//div[@id="wrapper"]/h1/span/text()').extract()
        if (title !=[]):
            orderdict[u'书名'] = title[0]
        else:
            orderdict[u'书名'] = ''

        coverurlTmp = sel.xpath('//div[@id="mainpic"]/a/img/@src').extract()
        coverurl = str()
        if (coverurlTmp != []):
            coverurlv = coverurlTmp[0]
            if ('mpic' in coverurlv):
                coverurl = coverurlv.replace('mpic','lpic')
        orderdict[u'书籍封面'] = coverurl

        rateTmp1 = sel.xpath('//div[@class="rating_wrap"]/p/strong/text()').extract()
        rateTmp2 = sel.xpath('//strong[@class="ll rating_num "]/text()').extract()
        rate = str()
        if (rateTmp1 != []):
            rate = rateTmp1[0].strip()
        elif(rateTmp2 != []):
            rate = rateTmp2[0].strip()
        else:
            pass

        orderdict[u'评分'] = rate

        #!< 作者，出版社，原书名，译者，出版年，页数，定价，装帧，丛书，ISBN
        sels = sel.xpath('//div[@id="info"]/span')

        for tree in sels:

            tv = tree.xpath('text()').extract()
            tv = tv[0].strip(':') if (tv!=[]) else ('') # title value

            # 作者，译者
            tvs = tree.xpath('span/text()').extract()
            tvs = tvs[0].strip() if (tvs!=[]) else ('')
            if (tvs != ''):
                tv = tvs

            # 其他
            afind = str()
            afind = tree.xpath('following-sibling::text()').extract_first().strip()

            if (afind == ''):
                # 作者，译者
                av = tree.xpath('a/text()').extract()
                av = av[0].strip() if (av!=[]) else ('') # <a> text </a>
                if (av == ''):
                    # 丛书
                    avs = sel.xpath('//div[@id="info"]/a/text()').extract()
                    avs = avs[0].strip() if (avs!=[]) else ('')
                    afind = avs
                else:
                    afind = av
            orderdict[tv] = afind


        #!< 内容简介 & 作者简介
        titles = sel.xpath('//div[@class="related_info"]/h2')
        values = sel.xpath('//div[@class="related_info"]/div')

        if (values != []):

            lenth = len(titles) if (len(titles)<=len(values)) else len(values)
            flag = True if (values[0].xpath('div[@class="ebook-promotion"]')) else False

            if flag:
                for i in xrange(lenth):

                    title = titles[i]
                    t = title.xpath('span/text()').extract()
                    t = t[0] if (t!=[]) else ('')

                    content = list()
                    if (values[i].xpath('div[@class="ebook-promotion"]')):

                        contenttmp = values[i+1].xpath('span[@class="all hidden"]/div/div[@class="intro"]/p/text()').extract()
                        if contenttmp:
                            content = contenttmp
                        else:
                            content = values[i+1].xpath('div/div[@class="intro"]/p/text()').extract()

                    else:

                        contenttmp = values[i+1].xpath('span[@class="all hidden"]/div/div[@class="intro"]/p/text()').extract()
                        if contenttmp:
                            content = contenttmp
                        else:
                            content = values[i+1].xpath('div/div[@class="intro"]/p/text()').extract()

                    if (i<2):
                        orderdict[t] = content
            else:
                for i in xrange(lenth):
                    title = titles[i]
                    t = title.xpath('span/text()').extract()
                    t = t[0] if (t!=[]) else ('')

                    content = list()
                    contenttmp = values[i].xpath('span[@class="all hidden"]/div/div[@class="intro"]/p/text()').extract()
                    if contenttmp:
                        content = contenttmp
                    else:
                        content = values[i].xpath('div/div[@class="intro"]/p/text()').extract()
                    orderdict[t] = content

        #!< 标签
        tags = sel.xpath('//div[@class="indent"]/span/a/text()').extract()
        tags = tags if (tags != []) else ('')
        orderdict[u'标签'] = tags

        #!< 相关推荐书目
        recom = sel.xpath('//div[@class="content clearfix"]/dl/dt/a/@href').extract()
        if (recom != []):
            subjectid = [ s[-9:-1] for s in recom]
            orderdict[u'相关推荐书目'] = subjectid
        else:
            orderdict[u'相关推荐书目'] = ''

        #!< 书籍购买来源
        buybook = sel.xpath('//ul[@class="bs noline more-after "]/li/a/@href').extract()
        buybook = buybook if (buybook != []) else ('')
        orderdict[u'书籍购买来源'] = buybook

        #!< 书籍链接
        bookurl  = response.url
        urlstate = response.status

        orderdict[u'书籍链接'] = bookurl

        #!< return data to 192.168.100.3:5000 !!! !!! !!!
        #posturl = str()
        if (200<=urlstate<400):
            #!< visitedurls !!!
            urldt = {}
            urldt = {'url':bookurl, 'spider':self.name}
            self.visitedurldict['urls'].append(urldt)

            #!< datas !!!
            bookdt = {}
            bookdt = {'url':bookurl, 'data':orderdict, 'spider':self.name}
            self.datadict['datas'].append(bookdt)

            #!< file !!!
            filedt = {}
            filedt = {
                        'url':bookurl,
                        'head':response.headers.to_string(),
                        'body':response.body,
                        'spider':self.name
                    }
            self.filedict['files'].append(filedt)
        else:
            #!< deadurls !!!
            urldt = {}
            urldt = {'url':bookurl, 'spider':self.name}
            self.deadurldict['urls'].append(urldt)

    # !< overwrite!
    def spider_closed(self, spider):
        """
        Put visitedurldict, datadict, filedict,  deadurldict to Master.
        Format:
        visitedurldict['urls'] = [ {'url':'', 'spider':self.name},  {'url':'', 'spider':self.name} ]

        datadict['datas']      = [ {'url':'', 'data':{}, 'spider':self.name},  {'url':'', 'data':{}, 'spider':self.name} ]

        filedict['files']      = [ {'url':'', 'head':'', 'body':'', 'spider':self.name},  {'url':'', 'head':'', 'body':'', 'spider':self.name} ]

        deadurldict['urls']    = [ {'url':'', 'spider':self.name},  {'url':'', 'spider':self.name} ]
        """
        lenOfdeadUrls = len(self.deadurldict['urls'])
        logging.info('spidername ' + self.name + '!!!')
        logging.info('visitedurls' + str(len(self.visitedurldict['urls'])))
        logging.info('datadict   ' + str(len(self.datadict['datas'])))
        logging.info('filedict   ' + str(len(self.filedict['files'])))
        logging.info('deadurls   ' + str(len(self.deadurldict['urls'])))

        if (lenOfdeadUrls==10):
            unirest.timeout(180)
            resdeadurl = unirest.put(
                            "http://192.168.100.3:5000/deadurls",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.deadurldict)
                        )

        elif(lenOfdeadUrls==0):
            unirest.timeout(180)
            resvisitedurl = unirest.put(
                            "http://192.168.100.3:5000/visitedurls",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.visitedurldict)
                        )
            unirest.timeout(180)
            resdata = unirest.put(
                            "http://192.168.100.3:5000/data",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.datadict)
                         )
            unirest.timeout(180)
            resfile = unirest.put(
                            "http://192.168.100.3:5000/file",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.filedict)
                         )

        else:# lenOfdeadUrls in (0,10)
            unirest.timeout(180)
            resvisitedurl = unirest.put(
                            "http://192.168.100.3:5000/visitedurls",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.visitedurldict)
                        )
            unirest.timeout(180)
            resdata = unirest.put(
                            "http://192.168.100.3:5000/data",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.datadict)
                         )
            unirest.timeout(180)
            resfile = unirest.put(
                            "http://192.168.100.3:5000/file",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.filedict)
                         )
            unirest.timeout(180)
            resdeadurl = unirest.put(
                            "http://192.168.100.3:5000/deadurls",
                            headers={ "Accept": "application/json", "Content-Type": "application/json" },
                            params=json.dumps(self.deadurldict)
                        )

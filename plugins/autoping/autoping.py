# coding: utf-8

import logging
import xmlrpclib

from google.appengine.ext import webapp
from google.appengine.api import taskqueue

from micolog_plugin import *

DEFAULT_PING_LISTS = """http://blogsearch.google.com/ping/RPC2
http://ping.baidu.com/ping/RPC2
http://www.feedsky.com/api/RPC2
http://blog.youdao.com/ping/RPC2
http://www.zhuaxia.com/rpc/server.php
http://rpc.weblogs.com/RPC2
http://micolog-tribe.appspot.com/tools/rpc_handler
"""

class autoping(Plugin):
    def __init__(self):
        Plugin.__init__(self, __file__)
        self.author = "鸣"
        self.authoruri = "http://qhm123.appspot.com"
        self.uri = "http://qhm123.appspot.com"
        self.description = "当博客更新时，自动通知博客搜索引擎和RSS聚合网站，使博客更新内容尽快被检索。"
        self.name = "autoping"
        self.version = "0.1"
        self.register_action('save_post', self.save_post)
        self.register_urlhandler('/admin/pingservice/pingworker', PingWorkerHandler)
        
        pinglists = OptionSet.get_by_key_name('autoping_pinglists')
        if not pinglists:
            OptionSet.setValue('autoping_pinglists', DEFAULT_PING_LISTS)
        
    def get(self, page):
        pinglists = OptionSet.getValue('autoping_pinglists', '')
        return u'''<h3>Ping lists</h3>
<form action="" method="post">
    <textarea name="pinglists" id="pinglists" cols="60" rows="10">%s</textarea>
    <input name="submit" id="submit" type="submit" value="submit" />
</form>
如果您对Ping服务不是很了解，最好不要更改以上默认列表。''' % (pinglists,)
    
    def post(self, page):
        pinglists = page.param('pinglists')
        OptionSet.setValue('autoping_pinglists', pinglists)
        
        return self.get(page)

    def save_post(self, entry, *arg1, **arg2):
        if not entry.published:
            return
        site_domain = self.blog.baseurl
        site_name = self.blog.title
        entry_link = '%s/%s' % (site_domain, entry.link)
        
        # 使用taskqueue防止ping操作影响保存文章速度。
        queue = taskqueue.Queue('default')
        queue.add(taskqueue.Task(url='/admin/pingservice/pingworker', 
                                 params={'site_domain': site_domain,
                                         'site_name': site_name,
                                         'entry_link': entry_link,},
                                 retry_options=taskqueue.TaskRetryOptions(task_retry_limit=1)))

class PingWorkerHandler(webapp.RequestHandler):
    
    def post(self):      
        pinglists = OptionSet.getValue('autoping_pinglists', '')
        pinglists = pinglists.splitlines()
        site_domain = self.request.get('site_domain')
        site_name = self.request.get('site_name')
        entry_link = self.request.get('entry_link')
        
        for url in pinglists:
            try:
                server = xmlrpclib.ServerProxy(url)
            except:
                logging.error('Failed: Ping service: ' + url)
                return
            try:
                server.weblogUpdates.ping(site_name, site_domain, entry_link, site_domain + '/feed')
            except:
                try:
                    server.weblogUpdates.extendedPing(site_name, site_domain, entry_link, site_domain + '/feed')
                except:
                    logging.error('Failed: Ping service: ' + url)
            
            # NOTE: 各个ping服务商提供的返回结构不一（特别是badidu），无法统一进行判断，
            # 如果没有出现异常则认为Ping操作成功。
            logging.info('OK: Ping service: ' + url)


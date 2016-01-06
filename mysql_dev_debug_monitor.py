#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# start a websocket server,and user can set mysql master info send to server,
# then server start a thread to connect mysql the mysql server, 
# send the mysql update info to websocket client
# use can start a default mysql rep thread when start start the process by set proccess's param 
#
# @author <jc3wish@126.com>

#from pprint import pprint
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
from pymysqlreplication.event import (
    RotateEvent,
    QueryEvent
)

import time
import threading

import socket
import os
import sys
import fcntl
import struct
import json

from SimpleWebSocketServer import WebSocket, SimpleWebSocketServer, SimpleSSLWebSocketServer

from optparse import OptionParser

parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
parser.add_option("--dbhost", default='127.0.0.1', type='string', action="store", dest="dbhost", help="hostname (localhost)")
parser.add_option("--dbport", default=3306, type='int', action="store", dest="dbport", help="default (3306)")
parser.add_option("--listen", default=8000, type='int', action="store", dest="listen", help="default (8000)")
parser.add_option("--dbuser", default="", type='string', action="store", dest="dbuser", help="default (root)")
parser.add_option("--dbpwd", default="", type='string', action="store", dest="dbpwd", help="default '',and if you want to start defaut mysql monitor thread,you must set a password and not be ''")
parser.add_option("--log_file", default="mysql-bin.000011", type='string', action="store", dest="log_file", help="default (mysql-bin.000001)")
parser.add_option("--log_pos", default=107, type='int', action="store", dest="log_pos", help="default (107)")

(options, args) = parser.parse_args()

Default_MYSQL_SETTINGS = {
    "host": options.dbhost,
    "port": options.dbport,
    "user": options.dbuser,
    "passwd": options.dbpwd,
}
# websokcet 监控Ip,port 全局变量
WobSocketIp = "0.0.0.0"
WobSocketPort = options.listen
	
Default_Mysql_Log = {
	"log_file":options.log_file,
	"log_pos":options.log_pos
}

doDefaultMysqlMonitor = True
for key in Default_MYSQL_SETTINGS:
   if Default_MYSQL_SETTINGS[key] == "" and key != "passwd":
      doDefaultMysqlMonitor = False 

for key in Default_Mysql_Log:
   if Default_Mysql_Log[key] == "":
      doDefaultMysqlMonitor = False 

#默认监听Mysql线程key 全局变量
DefaultMysqlMonitorThreadKey = ""
if doDefaultMysqlMonitor == True:
   if Default_MYSQL_SETTINGS["passwd"] == "":
      Default_MYSQL_SETTINGS["passwd"] = raw_input("input mysql password:")
   DefaultMysqlMonitorThreadKey = Default_MYSQL_SETTINGS["host"]+":"+str(Default_MYSQL_SETTINGS["port"])

#监控mysql 线程池,global 
thread_pool = {}
#客户端连接池 global
clients={} 
#线程锁池 global
mutex = {} 

class websocket(WebSocket):
    #多个包发送到服务端再组合成一个字符串
    linkinfo = ""
    #连接Key信息
    connectinfo = ""
    def handleMessage(self):
       #如果发送过来的数据是特定数字1，是心跳
       if self.data == "1":
          return
       self.linkinfo += self.data
       # 每次接收100个字符，假如少于这个数说明已经接收完了
       if len(self.data) == 100:
          return
       try:
          data = json.loads(self.linkinfo)
       except:
          print self.linkinfo + " is not a json data "
          self.linkinfo=""
          return
       #创建新连接线程
       if data["type"] == "create" or data["type"] == "link":
          MYSQL_SETTINGS = {
             "host":data["dbhost"],
             "port": data["dbport"],
             "user": data["dbuser"],
             "passwd": data["dbpwd"],
          }
          MYSQL_BinLog = {
             "log_file":data["log_file"],
             "log_pos": data["log_pos"],
          }
          key = MYSQL_SETTINGS["host"]+":"+str(MYSQL_SETTINGS["port"])
          #假如连接的是默认的监听mysql 线程，将直接转为 link 连接。不能杀死默认线程  print MYSQL_BinLog
          if DefaultMysqlMonitorThreadKey == key:
             data["type"] = "link"
          self.connectinfo = key
          #给当前mysql slave 信息连接创建一个线程锁，防止其他websocket 连接进来对这这个slave进行创建
          mutex[key] = threading.Lock()
       if data["type"] == "create":
          # 假如当前mysql监控已经存在 则先 把线程杀死 创建新线程, 加入线程锁，防止其他线程连接进来创建
          if mutex[key].acquire(2):
             returnData = createMonitorMysqlThread(key,MYSQL_BinLog,MYSQL_SETTINGS,)
             if returnData["status"] == True:
                clients[key]=[]
                clients[key].append(self)
             else:
                print returnData["msg"]
                self.sendMessage(u''+returnData["msg"])
                self.close()
                mutex[key].release()
                return
          mutex[key].release()

       elif data["type"] == "link":
             #假如线程池中已经有了当前mysql slave 线程，将直接在在当前mysql slave 线程的客户池中追加当前websocket，并加入线程锁，做到线程安全
             if thread_pool.has_key(key):
                if mutex[key].acquire(2):
                   if clients.has_key(key) == False:
                      clients[key]=[]
                      clients[key].append(self)
                   else:
                      clients[key].append(self)
                mutex[key].release()
             else:
                print "Error: no "+ key +"thread"
                self.sendMessage(u''+ "mysql monitor thread no exsit,you can use type:create try again!")
                self.close()
                return
       else:
          self.sendMessage(u''+ "Error: type must be create or link")
          self.close()
       return

    def handleConnected(self):
       print self.address, 'connected'

    def handleClose(self):
       #从用户连接池中删除
       clients.get(self.connectinfo).remove(self)

#发送信息
def sendMsg(key,data,timestamp):
	#return
	msg = json.dumps(data)
	#print msg
	#pushData.append(msg)
	if clients.has_key(key) == False:
		return
	if len(clients[key]) == 0:
		return
	for client in clients[key]:
		client.sendMessage(u''+str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(timestamp)))+"  "+msg)

def createMonitorMysqlThread(key,MYSQL_BinLog,MYSQL_SETTINGS):
   returnData = {
      "status":False,
      "msg":"default error",
   }
   # 假如当前mysql监控已经存在 则先 把线程杀死 创建新线程
   if thread_pool.has_key(key):
      try:
         thread_pool[key].join(0.2)
         if clients.has_key(key) == True:
            for client in clients[key]:
               client.close()
      except:
         del thread_pool[key] #删除线程key
         #returnData["msg"] = "Error: no "+ key +"thread"
         print "Error: no "+ key +"thread"
   try:
      thread_pool[key] = threading.Thread(target=doRep, args=(MYSQL_BinLog,MYSQL_SETTINGS,))
      thread_pool[key].setDaemon(True)
      thread_pool[key].start()
      returnData = {
         "status" : True,
         "msg":"success",
      }
   except:
      del thread_pool[key] #删除线程key
      returnData["msg"] = "Error: unable to start thread :"+key

   return returnData

def main():
	print "start..."
	if doDefaultMysqlMonitor == True:
		#开启默认监听mysql 线程，假如开始失败，将直接结束进程，这里不能用try，因为方法里面有抛异常，并且方法里只会返回指定格式的字典
		returnData = createMonitorMysqlThread(DefaultMysqlMonitorThreadKey,Default_Mysql_Log,Default_MYSQL_SETTINGS,)
		if returnData["status"] == True:
			print "start DefaultMysqlMonitorThread "+ DefaultMysqlMonitorThreadKey + "..."
		else:
			print returnData["msg"]
			sys.exit(0)
	else:
		print "Hadn't start default mysql monitor thread,if you want start,you can use --help";
			
	try:
		#开启websocket线程
		doWebSocket(WobSocketIp,WobSocketPort,)
		#thread.start_new_thread( doWebSocket, (WobSocketIp,WobSocketPort,) )
	except Exception,e:
		print "Error: unable to start websocket server,error : " ,e
		print "system exit out success"
		sys.exit(0)

	while 1:
	   pass	

#监听方法
def doRep(logPosConObj,MYSQL_SETTINGS):
	key = MYSQL_SETTINGS["host"]+":"+str(MYSQL_SETTINGS["port"])
	try:
		stream = BinLogStreamReader(
			connection_settings=MYSQL_SETTINGS,server_id=100,
			only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent, RotateEvent,QueryEvent],blocking=True,
			log_file=logPosConObj["log_file"],log_pos=logPosConObj["log_pos"])
		for binlogevent in stream:
			#prefix = "%s:%s:" % (binlogevent.schema, binlogevent.table)
		
			if isinstance(binlogevent, RotateEvent):
				#pprint (vars(binlogevent.packet))
				logPosConObj["log_file"]=binlogevent.packet.event.next_binlog
				logPosConObj["log_pos"]=binlogevent.packet.log_pos
				#logPosObject.setData(logPosConObj)
				continue
			if isinstance(binlogevent, QueryEvent):
				#pprint (vars(binlogevent.packet))
				sendMsg(key,binlogevent.query,binlogevent.timestamp)
				#logPosObject.setData(logPosConObj)
				continue
			for row in binlogevent.rows:
				#dbtable = binlogevent.schema+"_"+binlogevent.table
				if isinstance(binlogevent, DeleteRowsEvent):
					#print 'DeleteRowsEvent'
					sendMsg(key,row.get("values",object),binlogevent.timestamp)
					#func(row.get("values",object))
				elif isinstance(binlogevent, UpdateRowsEvent):
					#print 'UpdateRowsEvent'
					#print row
					sendMsg(key,row,binlogevent.timestamp)
					#func(row.get("after_values",object))
				elif isinstance(binlogevent, WriteRowsEvent):
					#print 'WriteRowsEvent'
					#print row
					sendMsg(key,row.get("values",object),binlogevent.timestamp)
					#func(row.get("values",object))
				#logPosConObj["log_pos"]=binlogevent.packet.log_pos
				#logPosObject.setData(logPosConObj)
		
		stream.close()
	except BaseException,e :
		print(e)
		return
		

#开启websocket
def doWebSocket(ip,port):
	server = SimpleWebSocketServer(ip, port, websocket)
	server.serveforever()
	
if __name__ == "__main__":
    main()

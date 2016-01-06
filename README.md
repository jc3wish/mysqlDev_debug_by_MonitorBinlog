mysqlDev-debug-by-monitorBinlog
========================

当前应用 是为了方便开发数据库的过程中，因为不同逻辑不同数据变更，为了更方便找出 逻辑bug，可以直接部署到团队测试服务器中，每个开发人员需要用到的时候，只需要把自己本机的db开始二进制日志，给于root一个非本地可以访问权限，把防火墙关闭，在网页上直接设置一下主库的信息就能实时查看到当前自己本机数据库的数据变更状态
还可以在启动这个进程的过程中指定默认数据库slave 监听线程，比如测试服务器数据库，这样其他开发或者测试人员，只要连接进来就能查看到测试服务器数据数据变更


启动进程
===========

python ./mysql_dev_debug_monitor.py --dbuser root --dbpwd root --dbport 3306 --dbhost 127.0.0.1 --log_file mysql-bin.000011 --log_pos 107 --listen 8000
 
* dbuser : 需要监听的数据库的用户名，默认为空
* dbpwd  ：数据库密码，默认为空
* dbport ：端口号，默认 3306
* dbhost ：ip地址，默认 本机
* log_file ：从哪一个二进制文件监听 默认为 mysql-bin.000001
* log_pos  ：position 位置

备：以上值都是 show master status查看到的信息，主从搭建的时候所需配置的

* listen  ：websocket 监听端口，需要防火墙打开端口

python ./mysql_dev_debug_monitor.py --help 帮助信息查看

websocket client
================
参数：需要被监听的数据库的主库信息，show master status 查看到的信息 （必须先开启二进制日志）

```
{"dbpwd": "test", "log_pos": 120, "dbhost": "192.168.2.181", "dbuser": "test", "log_file": "mysql-bin.000001", "type": "create", "dbport": 3306}

```

######type

* create : 重新创建新的mysql slave监听线程，会把其他websocket连接监听的线程kill掉创建新的，如果 dbhost+dbport == 进程启动的时候默信监听的slave库 将会转换为 link，并且其他参数无效
* link   : 如果当前mysql slave线程存在 ，则直接在现有的线程基础上监听，否则返回线程不存在

依懒包及下载地址
================
pymysql-0.6.7
https://github.com/PyMySQL/PyMySQL/releases/tag/0.6.7

pymysqlreplication-0.7
https://github.com/noplay/python-mysql-replication/releases/tag/0.7

SimpleWebSocketServer( 2015年最后更新代码 )
https://github.com/dpallot/simple-websocket-server   


备
================

代码只在linux python 2.6上测试过 ，再次感谢 提供包开源的开发者





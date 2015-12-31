#启动进程

python mysql_dev_debug_monitor.py --dbuser root --dbpwd root --dbhost 127.0.0.1 --log_file mysql-bin.000011 --log_pos 107 --listen 8000

#当--dbuser root --dbpwd root --dbport 3306 --dbhost 127.0.0.1 --log_file mysql-bin.000011 --log_pos 107 值 都设置了的时候，系统将会默认启动一个监听mysql 线程，并且其他websocket 连接进来的监听线程将不能杀死这个默认线程，只可以监听查看
#dbpwd 默认为空，并且这个值必须要有值才能启动
#python mysql_dev_debug_monitor.py --help 可以查看启动帮助

#--listen 8000  websocket 监听端口，防火墙要开启这个进程端口


#websocket 客户端 {"dbpwd": "root", "log_pos": 107, "dbhost": "127.0.0.1", "dbuser": "root", "log_file": "mysql-bin.000011", "type": "create", "dbport": 3306}

#type : 值可选 create,link ....
#		create:杀所有监听当前mysql的连接，并且重新开启一个mysql监听线程
#		link  :在所有mysql监听的基础创建一个连接
#其他参数都是mysql 主从配置中从库中要配置的参数

#ps: 要被监听mysql master 主机，相应的端口必须 开始，比如监听当前我这个开发机 192.168.1.188, 我这个开发机器上的 3306端口就要被放开，或者直接把防火墙给关闭，
#mysql_dev_debug_monitor.py 只在python 2.6 for linux 下的测试过，其他版本或者平台没有测试

#依懒包及下载地址：
#pymysql:https://github.com/PyMySQL/PyMySQL
#SimpleWebSocketServer : https://github.com/dpallot/simple-websocket-server   
#pymysqlreplication ： https://github.com/noplay/python-mysql-replication


#感谢几个开发者的开源
#SimpleWebSocketServer 在python linux 2.6即linux默认自带的版本中，242行 需要修改为： self.data = self.data.decode('utf8')，可能是版本问题，没具体去查阅，版本之间的具体差异


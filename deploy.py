#coding: utf-8
#version:2.1

'''
功能:
    1、可根据当前运行在tomcat下的所有项目进行判断、部署。
    2、部署更新后，如有问题可通过Email告知相关人员。
'''

__author__ = 'sundshinerj'

import re
import os
import time
import urllib
import shutil
import ftplib
import sys
import smtplib
import ConfigParser
import commands as cmd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

tomcat_path = '/usr/local/apache-tomcat-7.0.26'
IpCommd = "/sbin/ifconfig | grep 'inet addr:'|awk 'NR==1{print $2}'|awk -F: '{print $2}'"
Ip = cmd.getstatusoutput(IpCommd)[1]
TomcatShutdown = "/bin/kill `ps aux | /bin/grep -w apache-tomcat | /bin/grep -v grep | /usr/bin/awk '{print $2}'`"
TomcatStart = '/bin/sh ' + tomcat_path + '/bin/startup.sh>/dev/null'
now_t = time.strftime('%y%m%d%H%M%S')
now = time.strftime('%y%m%d%H%M%S')
Path = '/tmp/deploy'
#ftpserver
url = 'ftp地址'
user = '用户名'
passwd = '密码'
#mail
mail_list = ["你的email地址"]
mail_host = "smtp服务器"
mail_user = "用户名"
mail_passwd = "密码"
mail_postfix = "域名" #如：myemail.com

#必须为root帐户才能执行该脚本
if os.geteuid() != 0:
    file.writelines("[" + now + "]" + " This program must be run as root.Aborting.")
    file.close()
    sys.exit()

#如果没有日志目录就创建
log_dirs = ['logs', 'file', 'bak']
for dir in log_dirs:
    if os.path.exists('/tmp/deploy/' + dir):
        shutil.rmtree('/tmp/deploy/' + dir)
        os.makedirs('/tmp/deploy/' + dir)   
    else:
        os.makedirs('/tmp/deploy/' + dir)

file = open(Path + '/logs/' + Ip + '.log', 'a')
os.chdir('/tmp/deploy/file')
#下载项目包
def download_war():
    file.writelines("\n"+"[" + now + "]" + ' download now...\n')
    #从FTP上下载包
    ftp = ftplib.FTP(url)
    ftp.login(user, passwd)
    for war in war_lst:
        War = '/tmp/deploy/file/' + war
        try:
            fp = open(War, 'wb')
            ftp.retrbinary('RETR ' + war, fp.write)
            file.writelines("\n" + "[" + now + "]" + ' ' + war + ' is download\n')
            fp.close()
        except Exception:
            os.remove(War)
            file.writelines("\n" + "[" + now + "]" + ' no ' + war + ' on Ftp Server\n')
            fp.close()
    ftp.quit()

    if not os.listdir('/tmp/deploy/file/'):
        file.writelines("\n" + "[" + now + "]" + ' On the server without any of the available packages\n')
        file.close()
        print "script_result: False"
    else:
        war_up()

#更新项目包
def war_up():
    file.writelines("\n" + "[" + now + "]" + ' update server...\n')
    tomcat_log = tomcat_path + '/logs/catalina.out'
    os.system(TomcatShutdown)
    tomcat_log_bak = tomcat_log + now
    shutil.move(tomcat_log, tomcat_log_bak)
    
    for war in os.listdir('/tmp/deploy/file'):
        warfile = war.split('.')[0]
        shutil.rmtree(tomcat_path + '/webapps/' + warfile)
        shutil.move(tomcat_path + '/webapps/' + war, '/tmp/deploy/bak/')
        shutil.move('/tmp/deploy/file/' + war, tomcat_path + '/webapps/')
    
    if os.path.exists(tomcat_path+'work/Catalina'):
        shutil.rmtree(tomcat_path+'work/Catalina')
        
    os.system(TomcatStart)
    file.writelines("\n" + "[" + now + "]" + ' startup tomcat...\n')
    time.sleep(10)
    log_file = open(tomcat_log,'rb').readlines()
    for i in log_file:
        a = re.search('^ERROR -',i)
        if a is not None:
            file.writelines("\n" + "[" + now + "]" + ' start server Error,sendmaill to admin\n')
            os.system()
            file.writelines("\n" + "[" + now + "]" + ' Deploy is not successful!\n')
            print 'script_result: False'
            Str = "IP:%s\nServer:$s\nPlease open the Attachment"
            send_mail(mailto_list,"deploy_Error",Str)
            sys.exit()
    else:
        #os.system('/bin/sh '+tomcat_path+'bin/shutdown.sh>/dev/null')
        os.system(TomcatShutdown)
        shutil.move(tomcat_log_bak,tomcat_log)
        os.chdir(tomcat_path + '/webapps')
        os.system(TomcatStart)
        file.writelines("\n" + "[" + now + "]" + ' Deploy is successful!\n')
        file.close()
        print 'script_result: True'

#定义邮件内容
def send_mail(to_list,sub,content):
    me="ROOT"+"<"+mail_user+"@"+mail_postfix+">"
    #msg = MIMEText(content,_charset='gbk')
    msg = MIMEMultipart('related')
    msg['Subject'] = sub
    msg['From'] = me
    msg['To'] = ";".join(to_list)
    att = MIMEText(open(Path + '/logs/' + Ip + '.log', 'rb').read(), 'base64', 'utf-8')
    att["Content-Type"] = 'application/octet-stream'
    att["Content-Disposition"] = 'attachment; filename="' + Ip + 'ErrorLog.log"'
    msg.attach(att)
    try:
        s = smtplib.SMTP()
        s.connect(mail_host)
        s.login(mail_user,mail_pass)
        s.sendmail(me, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        print str(e)
        return False


#如果True，就执行download_war
s = os.listdir(tomcat_path + '/webapps')
war_lst = []
for i in s:
    if i.endswith('.war'):
        war_lst.append(i)
if war_lst:
    download_war()
else:
    file.writelines("\n" + "[" + now + "]" + "  The local war didn't find it\n")
    file.close()
    print "script_result: False"
    sys.exit()


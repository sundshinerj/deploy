#coding: utf-8
#version:2.2

'''
说明
1、为方便运维部署特编写此脚本
2、针对tomcat本地war包并从FTP服务器上获取相关资源
3、部署期间，如有问题则Email相关人员
'''

__author__ = 'sundshinerj'


#导入相关模块
import re
import socket
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


#定义相关变量参数
Way_list = []  #初使化war列表
Tomcat_path = '/usr/local/apache-tomcat-7.0.26'  #指定tomcat路径(最后不能有“/”)
Hostname = socket.getHostname()  #设置主机唯一标识
Tomcatshutdown = "/bin/kill `ps aux | /bin/grep -w apache-tomcat | /bin/grep -v grep | /usr/bin/awk '{print $2}'`"  #关闭tomcat
Tomcatstart = '/bin/sh ' + Tomcat_path + '/bin/startup.sh>/dev/null'  #启动tomcat
Now = time.strftime('%y%m%d%H%M%S')  #获取当前时间
Path = '/tmp/deploy'  #定义临时目录
Ftp_url = 'ftp地址'  #ftp地址
Ftp_u = 'ftp用户'  #用户
Ftp_p = 'ftp密码'  #密码
Mail_list = ['user1@test.com'] #邮件收件人列表，多个以逗号隔开。如：['user1@myemail.com','user2@myemail2.com']
Mail_host = 'smtp.test.com'  #发件箱地址
Mail_u = 'testuser'  #发件人
Mail_p = '123456'   #发件人密码
Mail_postfix = 'test.com' #如：邮箱域名


#必须为root帐户才能执行该脚本
if os.geteuid() != 0:
    file.writelines("[" + Now + "]" + " This program must be run as root.Aborting.")
    file.close()
    sys.exit()

    
#创建相关目录
log_dirs = ['logs', 'file', 'bak']
for dir in log_dirs:
    if os.path.exists('/tmp/deploy/' + dir):
        shutil.rmtree('/tmp/deploy/' + dir)
        os.makedirs('/tmp/deploy/' + dir)   
    else:
        os.makedirs('/tmp/deploy/' + dir)

#打开日志文件并记录相关内容        
file = open(Path + '/logs/' + Hostname + '.log', 'a')
os.chdir('/tmp/deploy/file')


#下载操作
def download_war():
    file.writelines("\n"+"[" + Now + "]" + " download Now...\n")
    ftp = ftplib.FTP(Ftp_url)
    ftp.login(Ftp_u, Ftp_p)
    for war in Way_list:
        War = '/tmp/deploy/file/' + war
        try:
            fp = open(War, "wb")
            ftp.retrbinary("RETR " + war, fp.write)
            file.writelines("\n" + "[" + Now + "]" + " " + war + " is download\n")
            fp.close()
        except Exception:
            os.remove(War)
            file.writelines("\n" + "[" + Now + "]" + " no " + war + " on Ftp Server\n")
            fp.close()
    ftp.quit()
    if not os.listdir('/tmp/deploy/file/'):
        file.writelines("\n" + "[" + Now + "]" + " On the server without any of the available packages\n")
        file.close()
        print "script_result: False"
    else:
        war_up()
        
#更新war
def war_up():
    file.writelines("\n" + "[" + Now + "]" + ' update server...\n')
    tomcat_log = Tomcat_path + '/logs/catalina.out'
    os.system(Tomcatshutdown)
    tomcat_log_bak = tomcat_log + Now
    shutil.move(tomcat_log, tomcat_log_bak)    
    for war in os.listdir('/tmp/deploy/file'):
        warfile = war.split('.')[0]
        shutil.rmtree(Tomcat_path + '/webapps/' + warfile)
        shutil.move(Tomcat_path + '/webapps/' + war, '/tmp/deploy/bak/')
        shutil.move('/tmp/deploy/file/' + war, Tomcat_path + '/webapps/')    
    if os.path.exists(Tomcat_path+'work/Catalina'):
        shutil.rmtree(Tomcat_path+'work/Catalina')
    os.system(Tomcatstart)
    file.writelines("\n" + "[" + Now + "]" + " startup tomcat...\n")
    time.sleep(10)
    log_file = open(tomcat_log,"rb").readlines()
    for i in log_file:
        a = re.search('^ERROR -',i)
        if a is not None:
            file.writelines("\n" + "[" + Now + "]" + " start server Error,sendmaill to admin\n")
            file.writelines("\n" + "[" + Now + "]" + " Deploy is not successful!\n")
            file.writelines(log_file)
            print "script_result: False"
            file.close()
            Str = "Server:%s\nPlease open the Attachment" % Hostname
            send_mail(Mail_list,"deploy_Error",Str)
            sys.exit()            
    else:
        os.system(Tomcatshutdown)
        shutil.move(tomcat_log_bak,tomcat_log)
        os.chdir(Tomcat_path + '/webapps')
        os.system(Tomcatstart)
        file.writelines("\n" + "[" + Now + "]" + " Deploy is successful!\n")
        file.close()
        print "script_result: True"
        
#定义邮件内容
def send_mail(to_list,sub,content):
    me = "ROOT" + "<" + Mail_u + "@" + Mail_postfix + ">"
    msg = MIMEMultipart('related')
    msg['Subject'] = sub
    msg['From'] = me
    msg['To'] = ";".join(to_list)
    att = MIMEText(open(Path + '/logs/' + Hostname + '.log', 'rb').read(), 'base64', 'utf-8')
    att["Content-Type"] = 'application/octet-stream'
    att["Content-Disposition"] = 'attachment; filename="' + Hostname + 'ErrorLog.log"'
    msg.attach(att)
    try:
        s = smtplib.SMTP()
        s.connect(Mail_host)
        s.login(Mail_u,Mail_p)
        s.sendmail(me, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        print str(e)
        return False
    
    
if __name__ == '__main__':
    s = os.listdir(Tomcat_path + '/webapps')
    for i in s:
        if i.endswith('.war'):
            Way_list.append(i)
    if Way_list:
        download_war()
    else:
        file.writelines("\n" + "[" + Now + "]" + "  The local war didn't find it\n")
        file.close()
        print "script_result: False"
        sys.exit()

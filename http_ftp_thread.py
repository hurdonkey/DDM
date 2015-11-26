#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Author: [Hurd]Donkey
Date: 2015-11-20
Description:
 A HTTP & FTP downloader with threads. Just send range request then recv and write orderly. Try "%prog -h" and get help.
 Check http donwload function:
 Excute "%prog -u "http://download.firefox.com.cn/releases/firefox/42.0/zh-CN/Firefox-latest-x86_64.tar.bz2" -o Firefox-latest-x86_64.tar.bz2.a -t 8"
 "wget http://download.firefox.com.cn/releases/firefox/42.0/zh-CN/Firefox-latest-x86_64.tar.bz2 -O Firefox-latest-x86_64.tar.bz2.b"
 "md5sum Firefox-latest-x86_64.tar.bz2*"
 Check ftp donwload function:
 "$prog -u "ftp://ftp.muug.mb.ca/mirror/centos/6.7/updates/i386/Packages/firefox-38.3.0-2.el6.centos.i686.rpm" -t 2 -o firefox-38.3.0-2.el6.centos.i686.rpm.a"
 "wget "ftp://ftp.muug.mb.ca/mirror/centos/6.7/updates/i386/Packages/firefox-38.3.0-2.el6.centos.i686.rpm" -O firefox-38.3.0-2.el6.centos.i686.rpm.b"
 "md5sum firefox-38.3.0-2.el6.centos.i686.rpm*"
 Of course, compare the time they lost.
'''


import os
import sys
import urllib
import urllib2
import ftplib
import threading
import time
from optparse import OptionParser


#reload(sys)
#sys.setdefaultencoding('utf8')
filecoding='utf-8'
stdincoding=sys.getfilesystemencoding()

BUFFSIZE=1024*16
rlock_file=threading.RLock()
size_down=0


class CFtpInfo():
        ''' a class for ftp info from url '''
        def __init__(self, url):
                stmp=url.split('/')[2]
                ftp_path=url.split('/', 3)[3]
                if stmp.find('@')>=0:
                        ltmp=stmp.split('@')
                        if ltmp[0].find(':')>=0:
                                ltmp0=ltmp[0].split(':')
                                ftp_user=ltmp0[0]
                                ftp_pass=ltmp0[1]
                        else:
                                ftp_user="anonymous"
                                ftp_pass=""
                        stmp1=ltmp[1]
                else:
                        ftp_user="anonymous"
                        ftp_pass=""
                        stmp1=stmp

                ltmp1=stmp1.split(':')
                ftp_addr=ltmp1[0]
                if stmp1.find(':')>=0:
                        ftp_port=int(ltmp1[1])
                else:
                        ftp_port=21

                print ftp_user, ftp_pass, ftp_addr, ftp_port, ftp_path
                self.ftp_user=ftp_user
                self.ftp_pass=ftp_pass
                self.ftp_addr=ftp_addr
                self.ftp_port=ftp_port
                self.ftp_path=ftp_path
                print 'created new ftp server obj.'


def ftp_connect_login(oftp):
        ''' connnect and login ftp server '''
        fd_ftp=ftplib.FTP()
        fd_ftp.set_debuglevel(0)
        fd_ftp.connect(oftp.ftp_addr, oftp.ftp_port)
        fd_ftp.login(oftp.ftp_user, oftp.ftp_pass)
        return fd_ftp


def ftp_disconnect(fd_ftp):
        ''' disconnect ftp server '''
        fd_ftp.set_debuglevel(0)
        try:
                fd_ftp.quit()
        except:
                pass
        return


def ftp_getlen(oftp):
        ''' send SIZE request and get FTP file length '''
        fd_ftp=ftp_connect_login(oftp)

        ret=fd_ftp.sendcmd('SIZE %s' % oftp.ftp_path)
        #print ret

        len_total=ret.split()[1]
        ftp_disconnect(fd_ftp)

        return int(len_total)


#def get_method_head():
#        return 'HEAD'
def getlen(url):
        ''' send HEAD request and get HTTP file length '''
        #response=urllib.urlopen(url)                   #urlopen发送GET请求会将文件全部下载

        request=urllib2.Request(url)                    #发送HEAD请求 只从服务器获取头信息
        #request.get_method=get_method_head              #get_method是函数 要用函数直接赋值
        request.get_method=lambda : 'HEAD'
        try:
                response=urllib2.urlopen(request)
        except:
                print "Connect HTTP server error"
                exit(0)
        #print response.info()
        #print response.code

        len_total=response.info().getheaders('Content-Length')[0]
        response.close()
        return int(len_total)


def ftp_down(oftp, fd_save, range_start, range_end, n_thread):
        ''' thread function: download FTP target with REST and RETR request '''
        fd_ftp=ftp_connect_login(oftp)

        fd_ftp.voidcmd('TYPE I')
        fd_ftp.sendcmd('REST %s' % range_start)
        fd_ftpdata=fd_ftp.transfercmd('RETR %s' % oftp.ftp_path)     #ftp data fd

        offset=range_start
        while offset<range_end+1:
                if offset>range_end+1-BUFFSIZE:
                        content_block=fd_ftpdata.recv(range_end+1-offset)
                else:
                        content_block=fd_ftpdata.recv(BUFFSIZE)
                global rlock_file
                with rlock_file:
                        fd_save.seek(offset)
                        fd_save.write(content_block)
                        global size_down
                        size_down+=len(content_block)
                        #print "Thread %d piece %d done: %d-%d" % (n_thread, i, offset, offset+len(content_block)-1)
                offset+=len(content_block)
        print "Thread %d all done: %d-%d" % (n_thread, range_start, range_end)

        fd_ftpdata.close()
        ftp_disconnect(fd_ftp)
        return


def http_down(url, fd_save, range_start, range_end, n_thread):
        ''' thread function: download HTTP target with range request '''
        request=urllib2.Request(url)
        request.headers['Range']='bytes=%s-%s' % (range_start, range_end)
        try:
                response=urllib2.urlopen(request)
        except:
                print "Connect HTTP server error"
                exit(0)
        #print response.info()
        #print response.code

        offset=range_start
        while True:
                content_block=response.read(BUFFSIZE)
                if content_block == None or content_block == '':
                        print "Thread %d all done: %d-%d" % (n_thread, range_start, range_end)
                        break

                global rlock_file
                #if rlock_file.acquire(blocking=True):
                #        #blocking表示是否阻塞当前线程 如果成功地获得lock，则acquire()函数返回True
                #        #否则acquire()将被阻塞直到另一个线程中调用release()来将状态改为unlocked，然后acquire()才可以再次将状态置为locked 并返回True
                #        fd_save.seek(offset)
                #        fd_save.write(content_block)
                #        global size_down
                #        size_down+=len(content_block)
                #        #print "Thread %d piece %d done: %d-%d" % (n_thread, i, offset, offset+len(content_block)-1)
                #        rlock_file.release()

                with rlock_file:                       #用with代替acquire 和 release()
                        fd_save.seek(offset)
                        fd_save.write(content_block)
                        global size_down
                        size_down+=len(content_block)
                        #print "Thread %d piece %d done: %d-%d" % (n_thread, i, offset, offset+len(content_block)-1)

                offset+=len(content_block)
        response.close()
        return


def splitsize(len_total, n_thread):
        ''' splite size by thread number, return a list splited '''
        len_section, len_remainder=divmod(len_total, n_thread)
        i=0
        l_sp=[]
        while i<n_thread:
                if i==n_thread-1:
                        t=(i*len_section, len_total-1)
                else:
                        t=(i*len_section, (i+1)*len_section-1)
                l_sp.append(t)
                i+=1
        return l_sp


def showstat(len_total, time_start):
        ''' thread function: show download statistics per second '''
        while size_down <= len_total:
                time_lost=time.time()-time_start
                print "%d/%d [%.1f%%]\t%.3f Mbyte/s" % (size_down, len_total, round(float(size_down)/len_total, 3)*100, size_down/time_lost/(1024*1024))
                if size_down == len_total:
                        print "Total length: %.2f Mbyte\tTotal time: %.2f" % (len_total/(1024*1024), time_lost)
                        return
                else:
                        time.sleep(1)


def optioninit():
        ''' get check args and  options '''
        # set option parser
        parser=OptionParser(usage="Usage: %prog [options] -u <url> -o <output> -t <thread>")
        parser.add_option("-u", "--url",
                        action="store",
                        dest="url",
                        default=False,
                        help="url target")
        parser.add_option("-o", "--output",
                        action="store",
                        dest="output",
                        default="a.out",
                        help="file save path")
        parser.add_option("-t", "--thread",
                        action="store",
                        dest="thread",
                        default="1",
                        help="range with thread number")
        parser.add_option("-v", "--version",
                        action="store_true",
                        dest="show_version",
                        help="show prog version")

        # get option parser
        (options, args)=parser.parse_args()
        #print options           #options matched
        #print args              #else strings no matched

        #check option parser
        if options.show_version == True:
                print "====== \(^o^)/ ======="
                print "My Http & FTP downloader with threads. Enjoy it!"
                print "Version 0.1"
                exit(0)
        if options.url == False or args != []:
                parser.print_help()
                exit(0)
        url=options.url
        savename=options.output
        n_thread=int(options.thread)
        return url, savename, n_thread


def diffurltype(url):
        ''' diff url http or ftp '''
        type=url.split(':')[0]
        if type=="http" or type=="https":
                return "http"
        elif  type=="ftp":
                return "ftp"
        else:
                print "Error url type!"
                exit(0)


def main():
        url, savename, n_thread = optioninit()
        print url, savename, n_thread

        type=diffurltype(url)
        print type

        if type=="ftp":
                oftp=CFtpInfo(url)

        fd_save=open(savename, 'wb')

        if type=="http":
                len_total=getlen(url)
        else:
                len_total=ftp_getlen(oftp)
        print 'Content-Length: ', len_total

        l_sp=splitsize(len_total, n_thread)
        print 'Split section: ', l_sp

        time_start=time.time()

        #http_down(url, fd_save, 0, 4000, 0)
        #ftp_down(oftp, fd_save, 0, 4000, 0)

        #thread0=threading.Thread(target=http_down, args=(url, fd_save, 0, 4000, 0))
        #thread0=threading.Thread(target=ftp_down, args=(oftp, fd_save, 0, 4000, 0))
        #thread0.start()
        #thread0.join()

        l_thread=[]
        i=0
        while i < n_thread:
                if type=="http":
                        t=threading.Thread(target=http_down, args=(url, fd_save, l_sp[i][0], l_sp[i][1], i))
                else:
                        t=threading.Thread(target=ftp_down, args=(oftp, fd_save, l_sp[i][0], l_sp[i][1], i))
                l_thread.append(t)
                print 'A downloader thread created: %d-%d' % (l_sp[i][0], l_sp[i][1])
                i+=1

        t_stat=threading.Thread(target=showstat, args=(len_total, time_start))

        t_stat.start()
        for t in l_thread:
                t.start()
        t_stat.join()
        for t in l_thread:
                t.join()

        fd_save.close()


if __name__ == '__main__':
        main()


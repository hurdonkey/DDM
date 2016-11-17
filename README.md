# A HTTP & FTP downloader script with python threading(支持http和ftp多线程分段的下载脚本)
## Description
Just send range(http)/rest(ftp) request, recv and write into file descriptor orderly.

## Using
 - Try `%prog -h` and get help.

 - Check HTTP donwload:
```
%prog -u "http://download.firefox.com.cn/releases/firefox/42.0/zh-CN/Firefox-latest-x86_64.tar.bz2" -o Firefox-latest-x86_64.tar.bz2.a -t 8
wget http://download.firefox.com.cn/releases/firefox/42.0/zh-CN/Firefox-latest-x86_64.tar.bz2 -O Firefox-latest-x86_64.tar.bz2.b
md5sum Firefox-latest-x86_64.tar.bz2*
```

 - Check FTP donwload:
```
%prog -u "ftp://ftp.muug.mb.ca/mirror/centos/6.7/updates/i386/Packages/firefox-38.3.0-2.el6.centos.i686.rpm" -t 2 -o firefox-38.3.0-2.el6.centos.i686.rpm.a
wget "ftp://ftp.muug.mb.ca/mirror/centos/6.7/updates/i386/Packages/firefox-38.3.0-2.el6.centos.i686.rpm" -O firefox-38.3.0-2.el6.centos.i686.rpm.b
md5sum firefox-38.3.0-2.el6.centos.i686.rpm*
```
compare the time they lost.

## TODO
(1)debug option
(2)rate current not average

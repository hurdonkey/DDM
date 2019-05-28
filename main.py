# -*- coding: utf-8 -*-

""" Donkys Downloader by multi-range """

import os
from multiprocessing import Process, Pool, Manager, Queue, Lock, cpu_count
import requests
import argparse
from abc import ABCMeta, abstractmethod, abstractstaticmethod


class Downloader():
    __metaclass__ = ABCMeta

    def __init__(self, url, target_file_path, task_num):
        self.url = url
        self.target_file_path = target_file_path
        self.task_num = task_num
        self.length = None

    @abstractmethod
    def _get_length(self):
        """ 获取目标文件大小 """
        pass

    @abstractmethod
    def run_splited_task(self):
        pass

    def split_range(self):
        """ 按照目标大小和任务数对目标分片 """
        self._get_length()
        splited_range_list = []
        delta = self.length // self.task_num
        cursor = 0
        for i in range(self.task_num - 1):
            start = cursor
            end = cursor + delta
            range_tuple = (start, end)
            splited_range_list.append(range_tuple)
            cursor = end+1
        splited_range_list.append((cursor, self.length))
        return splited_range_list


class FTPDownloader(Downloader):
    # TODO: FTP downloader
    def __init__(self, ftp_url, ftp_name, ftp_pass, target_file_path, task_num):
        self.ftp_name = ftp_name
        self.ftp_pass = ftp_pass
        super().__init__(http_url, target_file_path, task_num)

    def _get_length(self):
        ret = self.fd_ftp.sendcmd('SIZE %s' % self.ftp_path)
        len_total = ret.split()[1]
        return int(len_total)

    def run_splited_task(self):
        pass


class HTTPDownloader(Downloader):
    def __init__(self, http_url, target_file_path, task_num):
        super().__init__(http_url, target_file_path, task_num)

    def _get_length(self):
        response = requests.head(self.url, headers={
            'accept-encoding': 'gzip;q=0,deflate,sdch',
        })
        print(response.headers)
        self.length = int(response.headers['Content-Length'])
        print(self.length)

    def run_splited_task(self, lock, range_start, range_end):
        pid = os.getpid()
        print("run task: %s-%s, process id: %s." % (range_start, range_end, pid))
        try:
            # 必须捕获 否则进程异常完全没有提示
            # 捕获手动输出异常也是有必要的

            response = requests.get(self.url, headers={
                'Range': 'bytes=%s-%s' % (range_start, range_end),
                'accept-encoding': 'gzip;q=0,deflate,sdch',
            })
            content = response.content

            offset = range_start

            # self.target_file_path = self.target_file_path + '_' + str(pid)
            print("%s get lock" % pid)
                
            with lock:
                with open(self.target_file_path,'a'):
                    # 创建空文件
                    # 后面必须用r+ 但是r+不能创建文件
                    pass

                with open(self.target_file_path, "rb+") as fd_target:
                    # 这里必须用r+ 每个进程要向文件相应的地方填入内容 为填入时都是\x00
                    # w回使用新文件, 之前线程的写入丢失
                    # a只能从尾部修改, 不能修改已存在的部分
                    fd_target.seek(offset, os.SEEK_SET)
                    fd_target.write(content)

                filesize = os.path.getsize(self.target_file_path)
                print("now file size:", filesize)

                # with open(self.target_file_path, "rb") as fd_target:
                #     print(fd_target.read())

            # TODO: recode downloaded size
            print("process %s ok, datalen: %s" % (pid, len(content)))

        except Exception as e:
            print(e)
            # TODO: 被主进程捕获 让主进程重新调用此任务


def optioninit():
    """ get check args and  options """
    parser = argparse.ArgumentParser(
        description='A testing simulation of HTTP Range and FTP RETR request with threads.')
    parser.add_argument(
        'url', help='url target', type=str)
    parser.add_argument(
        '-o', '--output', help='saved target path', type=str, default="a.out")
    parser.add_argument(
        '-t', '--tasks', help='number of tasks', type=int, default=1)
    return parser.parse_args()


def main():

    # 获取参数 url 存储的文件名 并发任务数
    # args = optioninit()
    # print(args)
    url = "http://download.firefox.com.cn/releases/firefox/42.0/zh-CN/Firefox-latest-x86_64.tar.bz2"
    # url = "http://192.168.137.10"
    output = "a.out"
    tasks = 3

    # 区别下载类型 声明下载对象
    # if "ftp:":
    #     downloader = FTPDownloader()
    # else:
    #     downloader = HTTPDownloader()
    downloader = HTTPDownloader(url, output, tasks)

    # 计算分割片段的范围
    splited_range_list = downloader.split_range()
    print(splited_range_list)

    # 先打开文件 而不是在每个进程里都打开
    # fd_target = open(output, 'wb')

    # 创建进程池
    lock = Manager().Lock()
    # queue = Manager().Queue()
    max_process_num = cpu_count() * 2
    process_num = tasks if tasks < max_process_num else max_process_num
    process_pool = Pool(process_num)

    # 加入任务
    for splited_range in splited_range_list:
        process_pool.apply_async(
            downloader.run_splited_task,
            args=(lock,) + splited_range
        )
    process_pool.close()

    # 当前进程主线程打印下载进度
    process_pool.join()


if __name__ == "__main__":
    main()
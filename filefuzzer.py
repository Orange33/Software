# 用于Windows的文件格式模糊器，
# 使用[pyzzuf]（https://github.com/nezlooy/pyzzuf）进行输入转换
# 并使用[winappdbg]（http://winappdbg.sourceforge.net/）进行崩溃检测。

# Usage
# -i : 输入目标文件目录
# -t : 目标文件类型，在文件目录中匹配
# -p : 目标可执行文件的路径 



from pyZZUF import *
from winappdbg import *
from time import time
import sys
import os
import argparse
import logging

# ZZUF配置
MIN_SEED = 1
MAX_SEED = 100
MIN_RATIO = 1
MAX_RATIO = 90
STEP = 10
TIMEOUT = 10


# 访问冲突处理
def crash_handler(event):
    name = event.get_event_name()
    code = event.get_event_code()
    pc = event.get_thread().get_pc()
    if code == win32.EXCEPTION_DEBUG_EVENT and event.is_last_chance():
        crash = Crash(event)
        data = crash.fetch_extra_data(event, takeMemorySnapshot=2)
        report = crash.signature
        event.get_process().kill()
        logging.warning("CRASH DETECTED: %s" % report)


# 启动进程、附加调试程序和监视崩溃
def debug_run(proc, mut_file):
    cmd = [proc, mut_file]
    dbg = Debug(crash_handler, bKillOnExit=True)
    logging.debug("Running cmd %s" % cmd)
    running = dbg.execv(cmd)
    #System.set_kill_on_exit_mode(True)
    max_time = time() + TIMEOUT
    while dbg and time() < max_time:
        try:
            dbg.wait(5000)
        except WindowsError, e:
            if e.winerror in (win32.ERROR_SEM_TIMEOUT, win32.WAIT_TIMEOUT):
                continue
            raise
        try:
            dbg.dispatch()
        finally:
            dbg.cont()
    dbg.kill(running.get_pid(), bIgnoreExceptions=True)
    logging.debug("Exiting %s" % cmd)
    return


# 转换测试用例文件并返回转换后文件路径 
def zzmutate(seed, ratio, input_file):
    ratio = float(ratio) / 100
    zzuf = pyZZUF(input_file)
    zzuf.set_seed(seed)
    zzuf.set_ratio(ratio)
    outfile = 's' + str(seed) + "__" + 'r' + str(ratio).replace('.', '_')
    with open(outfile, 'wb') as fout:
        mut_data = zzuf.mutate()
        fout.write(mut_data)
        fout.close()
    logging.debug("Testcase is %s" % outfile)
    file_path = os.getcwd() + '\\' + outfile
    return file_path


def main():
    logging.basicConfig(level=logging.debug)
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Input testcase folder")
    parser.add_argument("-t", "--type", help="Input filetype")
    parser.add_argument("-o", "--output", help="Output log file")
    parser.add_argument('-p', "--path", help="Path of target executable")
    args = parser.parse_args()

    if args.input:
        case_dir = args.input
    else:
        logging.error("No input testcase folder specified")
        sys.exit(1)
    if args.type:
        ext = args.type
    else:
        logging.error("No filetype specified. Exiting...")
        sys.exit(1)
    if args.path:
        proc = args.path

    print os.listdir(case_dir)
    for testcase in os.listdir(case_dir):
        print testcase
        if testcase.endswith(ext):
            if case_dir.endswith('\\'):
                f = open(case_dir + testcase)
            else:
                f = open(case_dir + '\\' + testcase)
            data = f.read()

    for seed in range(MIN_SEED, MAX_SEED, 1):
        for ratio in xrange(MIN_RATIO, MAX_RATIO, STEP):
            mut_file = zzmutate(seed, ratio, data)
            debug_run(proc, mut_file)
            os.remove(mut_file)

if __name__ == '__main__':
    main()

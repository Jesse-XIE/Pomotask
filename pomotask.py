from sys import stdout
from time import sleep
import sqlite3
import datetime
import os
import re
import subprocess
from config import Config


class Pomotask:

    def __init__(self):
        self.task = Task()
        self.init_notification()
        self.count = 0

    def init_notification(self):
        cwd = os.getcwd()
        icon_coffe = os.path.join(cwd, "coffe.png")
        icon_work = os.path.join(cwd, "work.png")

        if(Config.notif_type == 'buble'):
            def notif_break(msg):
                subprocess.call(["notify-send",
                                 msg,
                                 "-i",
                                 icon_coffe])

            def notif_work(msg):
                subprocess.call(["notify-send",
                                 msg,
                                 "-i",
                                 icon_work])
        elif(Config.notif_type == 'popup'):
            def notif_break(msg):
                subprocess.call(["zenity",
                                 "--info",
                                 "--title=pomotask",
                                 "--text='{}'".format(msg),
                                 "--window-icon=" + icon_coffe,
                                 "--width=100"])

            def notif_work(msg):
                subprocess.call(["zenity",
                                 "--info",
                                 "--title=pomotask",
                                 "--text='{}'".format(msg),
                                 "--window-icon=" + icon_work,
                                 "--width=100"])
        else:
            raise ValueError('Notification type unsupported: {}'
                             + Config.notif_type)
        self.notif_break = notif_break
        self.notif_work = notif_work

    def work(self, task_id, comment=''):
        now = datetime.datetime.now()
        print(' '*20 + 'work {} begins at: {}').format(task_id, str(now))
        # work
        self.timer(Config.pomodoro_time)
        # record
        self.task.record(task_id, duration=Config.pomodoro_time, comment=comment)
        self.count += 1
        # break
        if self.count % 4 == 0 :
            self.notif_break('Long break')
            print(' '*20 + 'long break... ')
            self.timer(Config.long_break_time)
        else:
            self.notif_break('Short break')
            print(' '*20 + 'short break... ')
            self.timer(Config.short_break_time)
        self.notif_work('Back to work')

    def timer(self, duration):
        for minute in range(duration-1, -1, -1):
            for second in range(59, -1, -1):
                stdout.write(
                    "\r" + " "*30 + "\x1B[1m\x1B[33m{:02d}:{:02d}\x1b[0m".format(minute, second))
                stdout.flush()
                sleep(1)
        stdout.write("\n")


class TaskTreeNode:

    def __init__(self, level, task):
        self.level = level
        self.task = task
        self.subs = []

    def read_sub_tasks(self, levels, tasks, i):
        self.subs = []
        while True:
            if i >= len(levels):
                return i
            level = levels[i]
            task = tasks[i]
            if level == self.level + 1:
                self.subs.append(TaskTreeNode(level, task))
                i = self.subs[-1].read_sub_tasks(levels, tasks, i + 1)
            elif level >= 0:
                return i


class Task:

    def __init__(self):
        self.load_from_file()
        self.db = TaskDB('tasks.sqlite3')
        self.sym_tomate = u"\U0001F345"
        self.sym_apple = u"\U0001F34E"

    def load_from_file(self, fname='tasks.md'):
        with open(fname, 'r+') as f:
            lines = f.readlines()
        levels = []
        tasks = []
        for line in lines:
            level, task = self._parse_task_line(line)
            if level >= 0:
                levels.append(level)
                tasks.append(task)
        self.root = TaskTreeNode(-1, '')
        self.root.read_sub_tasks(levels, tasks, 0)

    def _parse_task_line(self, line):
        pattern = re.compile(r'^(\s*)[*\-+]\s+([^/]*)\b')
        m = pattern.match(line)
        if m:
            level = len(m.group(1)) / Config.file_tab_size
            taskstr = m.group(2)
        else:
            level = -1
            taskstr = ''
        return (level, taskstr)

    def print_tree(self, offset=0, date_unit='day'):
        date_range = self.get_date_range(unit=date_unit, offset=offset)
        lines = ['']
        lines.append(' \x1b[1mCurrent task tree\x1b[0m')
        lines.append(' Statistic between\x1b[1m {} 00:00:00 \x1b[0m and \x1b[1m {} 00:00:00\x1b[0m'.format(
            date_range[0], date_range[1]))
        lines.append(' 1 tomate = {} min'.format(Config.pomodoro_time))
        title = self._tabular_line(
            ['Task', 'Tomates'], [50, 20], ['c', 'c'], bold_list=[True, True])
        title = '\x1b[31;40;1;4m' + title + '\x1b[0m'
        lines.append(title)
        for task_id, sub in enumerate(self.root.subs):
            self._print_recursive(
                sub, task_id, date_range, parent_task='', lines=lines)
        print '\n'.join(lines)

    def _print_recursive(self, node, task_id, time_range, parent_task, lines):
        task_cell = '{}--{} {}'.format(' ' *
                                       Config.print_tab_size * node.level, task_id, node.task)
        task_str = parent_task + '/' + node.task
        tomates = self.db.query_sum_duration(
            task_str + '%', time_range) / Config.pomodoro_time
        str_tomates = str(tomates) if tomates > 0 else '-'
        tomates_cell = ' ' * Config.print_tab_size * node.level + str_tomates
        color = '\x1b[3{};40m'.format(node.level+3)
        lines.append(
            color + self._tabular_line([task_cell, tomates_cell], [50, 20], ['l', 'l']) + '\x1b[0;0m')
        for task_id, sub in enumerate(node.subs):
            self._print_recursive(sub, task_id, time_range, task_str, lines)

    def _tabular_line(self, value_list, length_list, align_list=None, bold_list=None):
        if not align_list:
            align_list = ['l'] * len(value_list)
        if not bold_list:
            bold_list = [False] * len(value_list)
        line = '|'
        for v, l, a, b in zip(value_list, length_list, align_list, bold_list):
            if len(v) >= l-5:
                cell = ' ' + v[:l - 5] + '... '
            elif a == 'c':
                cell = ' ' * ((l - len(v)) / 2) + v
                cell = cell + ' ' * (l - len(cell))
            elif a == 'l':
                cell = ' ' + v + ' ' * (l - len(v) - 1)
            elif a == 'r':
                cell = ' ' * (l - len(v) - 1) + v + ' '
            line = line + cell + '|'
        return line

    def get_date_range(self, unit='day', offset=0):
        if offset < 0:
            raise ValueError('The offset parameter should be >= 0.')
        today = datetime.date.today()
        if unit == 'day':
            day1 = today
            if offset > 0:
                day1 -= datetime.timedelta(days=offset)
            day2 = day1 + datetime.timedelta(days=1)
        elif unit == 'week':
            day1 = today - datetime.timedelta(days=today.weekday())
            if offset > 0:
                day1 -= datetime.timedelta(days=offset * 7)
            day2 = day1 + datetime.timedelta(days=7)
        elif unit == 'month':
            year = today.year - (int((offset - today.month) / 12) + 1)
            month = 12 - (offset - today.month) % 12
            day1 = datetime.date(year, month, 1)
            _, last_day_num = calendar.monthrange(year, month)
            day2 = day1 + datetime.timedelta(days=last_day_num)
        elif unit == 'year':
            day1 = datetime.date(today.year - offset, 1, 1)
            day2 = datetime.date(today.year - offset + 1, 1, 1)
        else:
            raise ValueError('The parameter "{}" can\'t be parsed, please use'
                             'one of the following words: \n'
                             'today, week, month, year'.format(date))
        return (day1, day2)

    def query_task_duration(self, task, date):
        time_range = self._translate_date(date)
        return self.db.query_sum_duration(task, time_range)

    def record(self, task_id, duration=Config.pomodoro_time, comment='', time='now'):
        if time == 'now':
            time = str(datetime.datetime.now())
        ids = [int(s) for s in task_id.split('.')]
        task_str = self.get_task_by_ids(ids)
        self.db.record(time, task_str, duration, comment)

    def get_task_by_ids(self, ids):
        def get_task_by_ids_recursive(node, ids):
            if node.level < len(ids) - 1:
                sub_node = node.subs[ids[node.level + 1]]
                return node.task + '/' + get_task_by_ids_recursive(sub_node, ids)
            else:
                return node.task
        return get_task_by_ids_recursive(self.root, ids)

    def edit(self):
        subprocess.call([Config.editor, Config.task_file])


class TaskDB:

    def __init__(self, dbfile):
        # connect database
        self.conn = sqlite3.connect(dbfile)
        self.cur = self.conn.cursor()
        self.cur.execute(
            'CREATE TABLE IF NOT EXISTS '
            'Tasks (time TIME, task TEXT, '
            'duration INT, comment TEXT)')
        self.dbtuple = '(time, task, duration, comment)'

    def record(self, time, task, duration, comment):
        self.cur.execute('INSERT INTO Tasks ' + self.dbtuple +
                         ' VALUES (?, ?, ?, ?)',
                         (time, task, duration, comment))
        self.conn.commit()

    def query_sum_duration(self, task, time_range):
        durations = self.cur.execute("SELECT duration FROM Tasks WHERE task Like '{}' AND time BETWEEN '{}' AND '{}'".format(
            task, time_range[0], time_range[1]))
        return sum([d[0] for d in durations])

    def delete_last(self):
        self.cur.execute(
            'DELETE FROM Tasks WHERE time = (SELECT MAX(time) FROM Tasks)')


if __name__ == '__main__':
    pomo = Pomotask()
    task = pomo.task

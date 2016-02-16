import re
from datetime import datetime, date

from PySide import QtCore

from qtodotxt.lib.task_htmlizer import TaskHtmlizer


class Task(object):
    """
    Represent a task as defined in todo.txt format
    Take a line in todo.txt format as argument
    Arguments are read-only, reparse string to modify them or
    use one the modification methods such as setCompleted()
    """

    def __init__(self, line):
        settings = QtCore.QSettings()
        self._highest_priority = 'A'
        self._lowest_priority = settings.value("lowest_priority", "D")

        # define all class attributes here to avoid pylint warnings
        self.contexts = []
        self.projects = []
        self.priority = ""
        self.is_complete = False
        self.completion_date = None
        self.is_future = False
        self.text = ''
        self.due = None
        self.threshold = None
        self.keywords = {}

        self.parseLine(line)

    def __str__(self):
        return self.text

    def __repr__(self):
        return "Task({})".format(self.text)

    def _reset(self):
        self.contexts = []
        self.projects = []
        self.priority = ""
        self.is_complete = False
        self.completion_date = None
        self.is_future = False
        self.text = ''
        self.due = None
        self.threshold = None
        self.keywords = {}

    def parseLine(self, line):
        """
        parse a task formated as string in todo.txt format
        """
        self._reset()
        words = line.split(' ')
        if words[0] == "x":
            self.is_complete = True
            words = words[1:]
            # parse next word as a completion date
            # required by todotxt but often not here
            self.completion_date = self._parseDate(words[0])
            if self.completion_date:
                words = words[1:]
        elif re.search(r'^\([A-Z]\)$', words[0]):
            self.priority = words[0][1:-1]
            words = words[1:]
        for word in words:
            self._parseWord(word)
        self.text = line

    def _parseWord(self, word):
        if len(word) > 1:
            if word.startswith('@'):
                self.contexts.append(word[1:])
            elif word.startswith('+'):
                self.projects.append(word[1:])
            elif ":" in word:
                key, val = word.split(":", 1)
                self.keywords[key] = val
                if word.startswith('due:'):
                    self.due = self._parseDate(word[4:])
                elif word.startswith('t:'):
                    self.threshold = word[2:]
                    self.is_future = self._parseDate(word[2:])
                    if self.is_future and self.is_future <= date.today():
                        self.is_future = None

    def _parseDate(self, string, context=""):
        try:
            return datetime.strptime(string, '%Y-%m-%d').date()
        except ValueError:
            print("Error parsing date ", string)
            return None

    def setCompleted(self):
        """
        Set a task as completed by inserting a x and current date at the begynning of line
        """
        if self.is_complete:
            return
        self.completion_date = date.today()
        date_string = self.completion_date.strftime('%Y-%m-%d')
        self.text = 'x %s %s' % (date_string, self.text)
        self.is_complete = True

    def setPending(self):
        """
        Unset completed flag from task
        """
        if not self.is_complete:
            return
        words = self.text.split(" ")
        d = self._parseDate(words[1])
        if d:
            self.text = " ".join(words[2:])
        else:
            self.text = " ".join(words[1:])
        self.is_complete = False
        self.completion_date = None

    def toHtml(self):
        """
        return a task as an html block which is a pretty display of a line in todo.txt format
        """
        htmlizer = TaskHtmlizer()
        return htmlizer.task2html(self)

    def increasePriority(self):
        if self.is_complete:
            return
        if not self.priority:
            self.priority = self._lowest_priority
            self.text = "({}) {}".format(self.priority, self.text)
        elif self.priority != self._highest_priority:
            self.priority = chr(ord(self.priority) - 1)
            self.text = "({}) {}".format(self.priority, self.text[4:])

    def decreasePriority(self):
        if self.is_complete:
            return
        if self.priority >= self._lowest_priority:
            self.priority = ""
            self.text = self.text[4:]
            self.text = self.text.replace("({})".format(self.priority), "", 1)
        elif self.priority:
            oldpriority = self.priority
            self.priority = chr(ord(self.priority) + 1)
            self.text = self.text.replace("({})".format(oldpriority), "({})".format(self.priority), 1)

    def __eq__(self, other):
        return self.text == other.text

    def __lt__(self, other):
        if self.is_complete != other.is_complete:
            return self._lowerCompleteness(other)
        if self.priority != other.priority:
            if not self.priority:
                return True
            if not other.priority:
                return False
            return self.priority > other.priority
        # order the other tasks alphabetically
        return self.text > other.text

    def _lowerCompleteness(self, other):
        if self.is_complete and not other.is_complete:
            return True
        if not self.is_complete and other.is_complete:
            return False
        raise RuntimeError("Could not compare completeness of 2 tasks, please report")


def filterTasks(filters, tasks):
    if None in filters:  # FIXME: why??? if a filter is None we can just ignore it
        return tasks

    filteredTasks = []
    for task in tasks:
        for filter in filters:
            if filter.isMatch(task):
                filteredTasks.append(task)
                break
    return filteredTasks

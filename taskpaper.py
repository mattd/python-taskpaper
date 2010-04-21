"""
Created by Emil Erlandsson
Modified by Matt Dawson
Copyright (c) 2009 Matt Dawson

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

"""

class Node(object):
    """
    A generic node on a TaskPaper object.

    """
    def __init__(self, line):
        self.tabs = len(line) - len(line.lstrip('\t'))
        #self.line = unicode(line, "utf-8").strip()
        self.line = line.strip()
        self.name = ""
        self.parent = None
        self.children = []
        self.tags = []
        self._parse()

    def set_parent(self, parent):
        self.parent = parent

    def add_child(self, child):
        self.children.append(child)

    def add_tag(self, tag):
        self.tags.append(tag)

    def __str__(self):
        return "%(tabs)s%(line)s" % { 'tabs': (self.tabs*'\t'), 'line': self.line }


class ProjectNode(Node):
    """
    A project node on a TaskPaper object.

    """
    def _parse(self):
        line = self.line.strip()
        tokens = line.split("@")
        self.name = tokens[0][:-1].strip()
        self.tags = tokens[1:]

class TaskNode(Node):
    """
    A task node on a TaskPaper object.

    """
    def _parse(self):
        line = self.line.strip()
        tokens = line.split("@")
        self.name = tokens[0][2:].strip()
        self.tags = self._parse_tags(tokens[1:])

    def _parse_tags(self, tags):
        """
        >>> t = TaskNode("\t\t- Task @tag @tagWithValue(100)")
        >>> len(t.tags.keys())
        2
        >>> print t.tags['tag']
        None
        >>> print t.tags['tagWithValue']
        100
        """
        tag_dict = {}
        for tag in tags:
            name, value = self._parse_tag(tag)
            tag_dict[name] = value
        return tag_dict

    def _parse_tag(self, tag):
        tag = tag.strip()
        s = tag.split("(")
        return s[0], s[1][:-1] if len(s) == 2 else None

    def __str__(self):
        """
        >>> t = TaskNode("\t\t- Task @tag @tagWithValue(100)")
        >>> t.tags['tag'] = "value"
        >>> print t
        - Task @tag(value) @tagWithValue(100)
        """
        tags = ['@%s(%s)' % (t[0], t[1]) if t[1] else "@%s" % t[0] for t in self.tags.items()]
        return "%(tabs)s- %(name)s %(tags)s" % { 
                'tabs': (self.tabs * '\t'), 'name': self.name, 'tags': ' '.join(tags) }

class NoteNode(Node):
    """
    A note node on a TaskPaper object.

    """
    def _parse(self):
        line = self.line.strip()
        tokens = line.split("@")
        self.name = tokens[0].strip()
        self.tags = tokens[1:]

class TaskPaper(object):
    """
    A wrapper class for TaskPaper files.


    """
    def __init__(self, url):
        self.url = url 
        self.filename = url.split("/")[-1]
        self.children= []

    def add_child(self, node):
        """
        Adds a no-parent node to a TaskPaper object.

        """
        self.children.append(node)

    def filter_by_tag(self, tag_name):
        """
        >>> tp = parse_taskpaper('test.taskpaper')
        >>> tasks = tp.filter_by_tag("tag")
        >>> len(tasks)
        3
        >>> len(tp.filter_by_tag('tagWithValue'))
        1
        """
        def filter_nodes(nodes, tag_name):
            tasks = []
            for node in nodes:
                if isinstance(node, TaskNode) and tag_name in node.tags.keys():
                    tasks.append(node)
                tasks.extend(filter_nodes(node.children, tag_name))
            return tasks
        return filter_nodes(self.children, tag_name)

    def __str__(self):
        def to_string(nodes):
            output = [str(node) + '\n' + to_string(node.children) for node in nodes]
            return ''.join(output)
        tp_string = to_string(self.children)
        return tp_string

def parse_taskpaper_from_string(string):
    import StringIO
    handle = StringIO.StringIO()
    handle.write(string)
    handle.seek(0)

    return parse_taskpaper_from_file(handle)


def parse_taskpaper(url):
    """
    Parse a TaskPaper file and return a corresponding TaskPaper object.

    """
    handle = file(url)

    return parse_taskpaper_from_file(handle, url)

def parse_taskpaper_from_file(handle, url = ''):
    taskpaper = TaskPaper(url)
    last = None
    for line in handle.readlines():

        # Determine what kind of node is on the current line.
        if line.strip().startswith("- "):
            node = TaskNode(line)
        elif line.strip().endswith(":"):
            node = ProjectNode(line)
        elif line.strip() != '':
            node = NoteNode(line)
        else:
            # The line is blank.
            node = None

        # If the line is blank, ignore it.
        if node is not None:
            # If this is not the beginning of the document and the line is
            # tabbed, proceed.
            if (last is not None) and (node.tabs != 0):
                if (node.tabs > last.tabs) or (type(node) == NoteNode):
                    last.add_child(node)
                    node.set_parent(last)
                else:
                    if node.tabs < last.tabs:
                        # Climb the document until we reach the closest sibling.
                        while node.tabs < last.tabs:
                            last = last.parent
                    last.parent.add_child(node)
                    node.set_parent(last.parent)
            # If this is the beginning of the document or the line is not tabbed,
            # add the node as a child of the taskpaper document. 
            else:
                taskpaper.add_child(node)
                node.set_parent(taskpaper)

            # Unless the current node is a note, assign it to last for the next
            # iteration.
            if type(node) != NoteNode:
                last = node

    return taskpaper

def print_tree(node):
    """
    For any Taskpaper object, print it and a formatted tree of its descendants.

    """
    try:
        print node.filename
    except AttributeError:
        print (node.tabs * '\t') + node.line
    for child in node.children:
        print_tree(child)

def write_tree(node, url):
    f = open(url, 'wb')
    def to_string(nodes):
        output = [(node.tabs * '\t') + node.line + '\n' + to_string(node.children) for node in nodes]
        return ''.join(output)
    tp_string = to_string(node.children)
    f.write(tp_string)
    f.close()


#! env python3

from github3 import GitHub
from functools import total_ordering
import json
import sys
import argparse
from collections import defaultdict
import os


class Tree(dict):
    def __init__(self):
        self.nodes = []

    def __missing__(self, key):
        keys = key.split('/')
        key = keys[0]
        if key not in self.keys():
            self[key] = value = Tree()
        else:
            value = self[key]

        if len(keys) > 1:
            return value['/'.join(keys[1:])]
        else:
            return value

    def mdtoc(self, dep=0, name='ROOT', id_counter=None):
        if id_counter is None:
            id_counter = defaultdict(lambda: -1)

        name_id = name.lower().replace(' ', '-')
        id_counter[name_id] += 1
        name_id = (name_id + ('-' + str(id_counter[name_id])
                   if id_counter[name_id] != 0
                   else ""))

        print('{}* [{}](#{})'.format('  ' * dep, name, name_id))

        try:
            for tree_name, tree in sorted(self.items()):
                tree.mdtoc(dep + 1, tree_name, id_counter)
        except IndexError:
            pass

    def mdprint(self, dep=1, name='ROOT', node_md=str):
        print('{} {}'.format('#' * dep, name))

        for node in sorted(self.nodes):
            print('* {}'.format(node_md(node)))

        for tree_name, tree in sorted(self.items()):
            tree.mdprint(dep + 1, tree_name, node_md)


@total_ordering
class Repo(object):
    def __init__(self, repo):
        self.repo = repo

    @property
    def full_name(self):
        return str(self.repo)

    @property
    def owner(self):
        return self.repo.owner.login

    @property
    def name(self):
        return self.repo.name

    @property
    def url(self):
        return self.repo.html_url

    @property
    def description(self):
        return self.repo.description

    def __eq__(self, other):
        return (self.name.lower(), self.owner) \
                == (other.name.lower(), other.owner)

    def __lt__(self, other):
        return (self.name.lower(), self.owner) \
                < (other.name.lower(), other.owner)

    def __str__(self):
        return self.full_name


def get_star_repos(user):
    gh = GitHub()
    stars = gh.starred_by(user)
    return list(map(Repo, stars))


def get_alias_converter():
    if os.path.isfile('alias.json'):
        with open('alias.json', 'r') as alias_config:
            alias = json.load(alias_config, object_hook=dict)
    else:
        alias = {}

    def f(tag):
        for before, after in alias.items():
            if tag.startswith(before):
                tag = tag.replace(before, after, 1)
        return tag
    return f


def get_tag_getter():
    tag_dict = {}
    try:
        with open('tag.json', 'r') as tag_file:
            tag_dict = json.load(tag_file, object_hook=dict)
    except FileNotFoundError:
        pass

    def f(repo_name):
        if repo_name in tag_dict and len(tag_dict[repo_name]) > 0:
            return tag_dict[repo_name]
        else:
            return ['Other']
    return f


def gen(user):
    get_tag_of_repo = get_tag_getter()
    convert_alias = get_alias_converter()

    # build repo tree and repo tags
    repo_tree = Tree()
    repo_tag = {}
    for repo in get_star_repos(user):
        tags = list(map(convert_alias, get_tag_of_repo(repo.full_name)))
        repo_tag[repo.full_name] = tags
        for tag in tags:
            repo_tree[tag].nodes.append(repo)

    # overwrite tag.json
    with open('tag.json', 'w+') as tag_file:
        json.dump(repo_tag, tag_file, indent='    ', sort_keys=True)

    # print .md file
    print("# TOC")
    repo_tree.mdtoc(name="Star")
    print()
    repo_tree.mdprint(
        name='Star',
        node_md=lambda x: '[{}]({}): {}'.format(
                                                str(x), x.url, x.description))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='star')
    parser.add_argument('-u', '--user', help='GitHub user', required=True)

    args = parser.parse_args()

    gen(**args.__dict__)

#! env python3

from github3 import GitHub
from functools import total_ordering
import json
import argparse
from collections import defaultdict
import os
import textwrap


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

    def walk(self, dep=0, name='ROOT'):
        yield (name, dep, self)
        for tree_name, tree in sorted(self.items()):
            for item in tree.walk(dep + 1, tree_name):
                yield item


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
    used_id_counter = defaultdict(lambda: -1)

    def use_id(name):
        name_id = name.lower().replace(' ', '-')
        used_id_counter[name_id] += 1
        suffix = ('-' + str(used_id_counter[name_id])) \
            if used_id_counter[name_id] != 0 \
            else ""
        return f'{name_id}{suffix}'

    print(textwrap.dedent("""\
        # Usage

        1. generate a new repository from this template
        1. trigger github action

        # Inspiration

        * [maguowei/starred](https://github.com/maguowei/starred):
          creating your own Awesome List by GitHub stars!
    """))
    use_id('Usage')
    use_id('Inspiration')

    print("# Contents")
    use_id('Contents')
    print()
    for name, dep, item in repo_tree.walk():
        if dep == 0:
            continue

        print('{}* [{}](#{})'.format(
            '  ' * (dep - 1),
            name,
            use_id(name))
        )
    print()

    for name, dep, item in repo_tree.walk():
        if dep == 0:
            continue

        print('{} {}'.format('#' * dep, name))
        print()

        for node in sorted(item.nodes):
            print('* [{}]({}): {}'.format(
                str(node), node.url, node.description
            ))
        print()
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='star')
    parser.add_argument('-u', '--user', help='GitHub user', required=True)

    args = parser.parse_args()

    gen(**args.__dict__)

from github3 import GitHub
from functools import total_ordering
import json
import sys
import argparse


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


class RepoTagDict(dict):
    def __missing__(self, key):
        self[key] = value = []
        return value

def gen(token):
    gh = GitHub(token=token)
    stars = gh.starred()

    taged_star_tree = Tree()

    try:
        with open('tag.json', 'r') as tag_file:
            repo_tag_dict = json.load(tag_file, object_hook=RepoTagDict)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        print("invalid tag", file=sys.stderr)
        repo_tag_dict = RepoTagDict()

    for star in stars:
        repo = Repo(star)
        taged_star_tree['Language'][star.language or 'Null'].nodes.append(repo)

        for tag in repo_tag_dict[repo.full_name]:
            taged_star_tree[tag].nodes.append(repo)

    with open('tag.json', 'w+') as tag_file:
        json.dump(repo_tag_dict, tag_file, indent='    ', sort_keys=True)

        taged_star_tree.mdprint(
            name='Star',
            node_md=lambda x: '[{}]({}): {}'.format(
                                                str(x), x.url, x.description))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='star')
    parser.add_argument('-t', '--token', help='GitHub token', required=True)

    args = parser.parse_args()

    gen(**args.__dict__)

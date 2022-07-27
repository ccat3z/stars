#! env python3

from github3.github import GitHub
from github3.repos.repo import ShortRepository
from functools import total_ordering, lru_cache
import json
import argparse
from collections import defaultdict
import os
import textwrap
import logging

logging.basicConfig(level=logging.DEBUG)


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
class Repo(dict):
    def __init__(self, repo):
        if isinstance(repo, ShortRepository):
            super().__init__(repo.as_dict())
        elif isinstance(repo, dict):
            super().__init__(repo)
        else:
            raise Exception('repo should be a ShortRepository or dict, but repo is {}'.format(type(self.repo)))

    @property
    def full_name(self):
        return self['full_name']

    @property
    def owner(self):
        return self['owner']['login']

    @property
    def name(self):
        return self['name']

    @property
    def url(self):
        return self['html_url']

    @property
    def description(self):
        return self['description']

    def __eq__(self, other):
        return (self.name.lower(), self.owner) \
                == (other.name.lower(), other.owner)

    def __lt__(self, other):
        return (self.name.lower(), self.owner) \
                < (other.name.lower(), other.owner)

    def __str__(self):
        return self.full_name


class StarRepoCollector:
    def __init__(self, gh, user, use_cache):
        self.gh = gh
        self.user = user
        self.use_cache = use_cache

    @lru_cache()
    def star_repos(self):
        if self.use_cache and os.path.isfile('repos.json'):
            logging.debug('loading star repos from repos.json...')
            with open('repos.json', 'r') as f:
                return json.load(f, object_hook=Repo)

        logging.debug('loading star repos from github...')
        stars = self.gh.starred_by(self.user)

        repos = list(map(Repo, stars))
        with open('repos.json', 'w+') as f:
            json.dump(repos, f)
        return repos

    @property
    @lru_cache()
    def resolve_alias(self):
        if os.path.isfile('alias.json'):
            logging.debug('load tag alias from alias.json...')
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

    @property
    @lru_cache()
    def get_repo_tags(self):
        tag_dict = {}
        try:
            logging.debug('try to load tag.json...')
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


    def gen_markdown(self):
        # build repo tree and repo tags
        repo_tree = Tree()
        repo_tag = {}
        for repo in self.star_repos():
            tags = list(map(self.resolve_alias, self.get_repo_tags(repo.full_name)))
            repo_tag[repo.full_name] = tags
            for tag in tags:
                repo_tree[tag].nodes.append(repo)

        # overwrite tag.json
        with open('tag.json', 'w+') as tag_file:
            json.dump(repo_tag, tag_file, indent='    ', sort_keys=True)

        # print .md file
        used_id_counter = defaultdict(lambda: -1)

        def id_of_name(name):
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

        print("# Contents")
        print()
        for name, dep, item in repo_tree.walk():
            if dep == 0:
                continue

            print('{}* [{}](#{})'.format(
                '  ' * (dep - 1),
                name,
                id_of_name(name))
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
    parser.add_argument('--use-cache', action='store_true', help='Use local cache of github api')

    args = parser.parse_args()

    collector = StarRepoCollector(gh=GitHub(), **args.__dict__)
    collector.gen_markdown()

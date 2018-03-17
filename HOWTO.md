# How to use

1. fork this repo
2. remove `tag.json` and `README.md`
3. switch on the repo in Travis CI
4. generate [a personal access token](https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/) with the `public_repo` or `repo` scope (repo is required for private repositories)
5. set GITHUB_TOKEN env in Travis CI dashboard
6. trigger first build, tag.json will be generated
7. edit `tag.json`, CI will generate new README.md automatically

# About this repo

Generate awesome list from GitHub stars with tags

## Inspiration

[starred](https://github.com/maguowei/starred)

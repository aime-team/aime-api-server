## Setup Sphinx

If npm is not installed, run:

```bash
sudo apt install npm
```
Then install jsdoc via npm and requirements.txt via pip:

```bash
npm install -g jsdoc
cd /path/to/aime/api/repo/docs
pip install -r requirements.txt
```

## Build Documentation

```bash
cd /path/to/aime/api/repo/docs
make clean
make html
```

## PublSpider

PublSpider is a network spider tool based on `scrapy`. It is designed to gather the information about academic publications.

### To start using PublSpider

It's necessary to install the `scrapy` library of python in advance.

```bash
pip install scrapy
```

### How to use

Firstly, ensure that your working directory is the root directory of this project. Then, edit `targets.json` and add some conferences you like to it.

> **Attention**: name of conferences in `targets.json` should be consistent with its respective name in [dblp](https://dblp.org/).
> 
> For example: I want to gather information about publications published in *USENIX ATC*, and the corresponding page on dblp is `https://dblp.org/db/conf/usenix/`, then I should add an `"usenix"` to `targets.json`.

After that, execute `scrapy crawl <media>` to start gathering information.

`<media>` is the media for storage. PublSpider currently supports two kinds of media:

#### sqlite

[sqlite](https://www.sqlite.org/index.html) is a library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine.

After executing `scrapy crawl sqlite`, a file names `data.db` should be generated in your working directory. feel free to browse it with any sqlite browser you like.

#### json

[json](https://www.json.org/json-en.html) is a lightweight data-interchange format. It is easy for humans to read and write. It is easy for machines to parse and generate.

After executing `scrapy crawl json`, a file names `data.json` should be generated in your working directory. JSON files could be viewed or edited by any text editor.

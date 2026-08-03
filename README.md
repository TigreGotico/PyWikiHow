# PyWikiHow

PyWikiHow is an unofficial Python API for WikiHow. It uses BeautifulSoup to scrape a WikiHow page and return structured data: an intro, an ordered list of steps, and a title. It also supports search and random-article lookup.

- [Installation](#installation)
- [Usage](#usage)
  * [Random How To](#random-how-to)
  * [Searching](#searching)
  * [Parsing](#parsing)
- [License](#license)

## Installation

```bash
pip install pywikihow
```

## Usage

### Random How To

Get a random WikiHow article.

```python
from pywikihow import RandomHowTo

how_to = RandomHowTo()
how_to.print()

```

### Searching

```python
from pywikihow import WikiHow, search_wikihow


max_results = 1  # default for optional argument is 10
how_tos = search_wikihow("how to learn programming", max_results)
assert len(how_tos) == 1
how_tos[0].print()


# for unlimited entries, use the generator instead
for how_to in WikiHow.search("how to learn python"):
    how_to.print()

```

### Parsing

Read and use `HowTo` objects.

```python
from pywikihow import HowTo

how_to = HowTo("https://www.wikihow.com/Train-a-Dog")

data = how_to.as_dict()

print(how_to.url)
print(how_to.title)
print(how_to.intro)
print(how_to.n_steps)
print(how_to.summary)

first_step = how_to.steps[0]
first_step.print()
data = first_step.as_dict()

how_to.print(extended=True)

```

Some articles divide their steps into parts. The `part` field of a step holds the name of its parent part.

```python
print(first_step.part)
```

Not every step has an illustration. When one exists, the `picture` field holds its URL; otherwise it is `None`.

```python
for step in how_to.steps:
    if step.picture:
        print(step.number, step.picture)
```

### ToDo

- Add parser for tips
- Add parser for warnings

## License

PyWikiHow is released under the [MIT License](LICENSE.md).

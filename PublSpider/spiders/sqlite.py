import scrapy
import time
import json
import sqlite3

# Get the published year from the name of conference
def parse_published_year(conference):
  pub_year = ''.join(list(filter(str.isdigit, conference)))
  if len(pub_year) == 2:
    pub_year = '19'+pub_year
  elif len(pub_year) > 4:
    pub_year = pub_year[:4]
  else:
    pass
  return int(pub_year)

def update_metrics(cursor, metrics):
  cursor.execute('''
    INSERT INTO metrics (title, abstract) VALUES (?, ?)
  ''', metrics)

class QuotesSpider(scrapy.Spider):
  name = "sqlite"
  download_delay = 1.1 # Avoid triggering robots.txt

  input_file = "targets.json"
  output_file = "data.db"
  scrap_list = []
  db = None

  def start_requests(self):

    # Initialization
    with open(self.input_file, "r") as f:
      self.scrap_list = json.load(f)
    self.db = sqlite3.connect(self.output_file)

    print()

    # Create Tables
    c = self.db.cursor()
    c.execute('''DROP TABLE IF EXISTS publications''')
    c.execute('''CREATE TABLE publications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT,
      published_year INTEGER,
      conference TEXT
      metrics_id INTEGER
    )''')
    c.execute('''DROP TABLE IF EXISTS publ_author''')
    c.execute('''CREATE TABLE publ_author (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      publ_id INTEGER NOT NULL,
      author_id INTEGER NOT NULL
    )''')
    c.execute('''DROP TABLE IF EXISTS authors''')
    c.execute('''CREATE TABLE authors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name KEY TEXT
    )''')
    c.execute('''DROP TABLE IF EXISTS metrics''')
    c.execute('''CREATE TABLE metrics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT,
      abstract TEXT
    )''')

    # Scrap
    for conf in self.scrap_list:
      yield scrapy.Request(url='https://dblp.org/db/conf/%s/' % conf, callback=self.parse)

  def parse(self, response):

    # Page in dblp.org
    if response.url.split("/")[2] == 'dblp.org':

      # This is the main page of a conference, add the content of each
      # conference to the request list.
      conflist = response.css("cite.data a.toc-link::attr(href)").getall()
      if conflist is not None:
        for content in conflist:
          conf = ''.join(list(filter(str.isalpha, content.split('/')[-1].split('.')[0])))
          if conf in self.scrap_list:
            content = response.urljoin(content)
            yield scrapy.Request(content, callback=self.parse)

      # This is the content page, parse all publications' information
      # and store them to database
      pub_from = response.url.split("/")[-1].split(".")[0]
      if pub_from is not '': # Filter out irrelevant information
        c = self.db.cursor()
        for line in response.css("li.inproceedings"):
          publication = line.css("cite.data")

          # Get metrics if allowed by user
          if self.settings.attributes['CRAWL_METRICS'].value == True:
            link = line.css("nav.publ ul li.drop-down div.head a::attr(href)").get()
            yield scrapy.Request(response.urljoin(link), callback=self.parse)

          # Insert the new publication and record its id
          c.execute('''
            INSERT INTO publications (title, published_year, conference)
            VALUES (?, ?, ?)''', (
              publication.css("span.title::text").get(),
              parse_published_year(pub_from),
              pub_from
          ))
          (publ_id, ) = c.execute("SELECT last_insert_rowid()").fetchone()

          # Insert authors
          for author in publication.css("span a span::text").getall():
            author_id = 0
            target_author = c.execute('''
              SELECT id FROM authors WHERE name = ?
            ''', (author, )).fetchone()

            # Avoid repeated insertion
            if target_author is not None:
              (author_id, ) = target_author
            else:
              c.execute('''
                INSERT INTO authors (name) VALUES (?)
              ''', (author, ))
              (author_id, ) = c.execute("SELECT last_insert_rowid()").fetchone()

            # Insert publ_author connections
            c.execute('''
              INSERT INTO publ_author (publ_id, author_id) VALUES (?, ?)
            ''', (publ_id, author_id))
    
    # Page in dl.acm.org
    elif response.url.split("/")[2] == 'dl.acm.org':
      title = response.css("h1.citation__title::text").get()
      abstract = response.css("div.article__body div.hlFld-Abstract div p::text").get()
      update_metrics(self.db.cursor(), (title, abstract))
    
    # Page in ieeexplore.ieee.org 
    elif response.url.split("/")[2] == 'ieeexplore.ieee.org':
      title = response.css("h1.document-title span::text").get()
      abstract = response.css("div.abstract-mobile-div div div div.u-pb-1 span::text").get()
      update_metrics(self.db.cursor(), (title, abstract))

    # Page in www.usenix.org
    elif response.url.split("/")[2] == 'www.usenix.org':
      raw_title = response.css("h1::text").get()
      if raw_title is None:
        raw_title = response.css("h2::text").get()
      title = ''.join(raw_title.split())
      abstract = ''
      for p in response.css('''div.field-name-field-paper-description 
        div.field-items div p::text''').getall():
        abstract += '\n' + p
      update_metrics(self.db.cursor(), (title, abstract))

    # For debugging
    else:
      print(response.url.split("/")[2])

    # Commit the changes
    self.db.commit()
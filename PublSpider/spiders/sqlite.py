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

class QuotesSpider(scrapy.Spider):
  name = "sqlite"
  download_delay = 1.5 # Avoid triggering robots.txt

  input_file = "targets.json"
  output_file = "data.db"
  scrap_list = []
  db = None

  def start_requests(self):

    # Initialization
    with open(self.input_file, "r") as f:
      self.scrap_list = json.load(f)
    self.db = sqlite3.connect(self.output_file)

    # Create Tables
    c = self.db.cursor()
    c.execute('''DROP TABLE IF EXISTS publications''')
    c.execute('''CREATE TABLE publications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT,
      published_year INTEGER,
      conference TEXT
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

    # Scrap
    for conf in self.scrap_list:
      yield scrapy.Request(url='https://dblp.org/db/conf/%s/' % conf, callback=self.parse)

  def parse(self, response):

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
      for publication in response.css("cite.data"):

        # Insert the new publication and record its id
        c.execute('''
          INSERT INTO publications (title, published_year, conference)
          VALUES (?, ?, ?)''', (
            publication.css("span.title::text").get(),
            parse_published_year(pub_from),
            pub_from
        ))
        (publ_id, ) = c.execute("SELECT last_insert_rowid()").fetchone()

        # Insert authors and publ_author connections
        for author in publication.css("span a span::text").getall():
          c.execute('''
            REPLACE INTO authors (name) VALUES (?)
          ''', (author, ))
          (author_id, ) = c.execute("SELECT last_insert_rowid()").fetchone()
          c.execute('''
            INSERT INTO publ_author (publ_id, author_id) VALUES (?, ?)
          ''', (publ_id, author_id))
      
      # Commit the changes
      self.db.commit()
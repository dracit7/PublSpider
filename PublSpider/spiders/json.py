import scrapy
import json


class QuotesSpider(scrapy.Spider):
  name = "json"
  download_delay = 1.5 # Avoid triggering robots.txt

  input_file = "targets.json"
  output_file = "data.json"
  scrap_list = []

  def start_requests(self):

    # Initialization
    with open(self.input_file, "r") as f:
      self.scrap_list = json.load(f)
    with open(self.output_file, "w") as f:
      f.write("{\n")

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
    # and store them to a file.
    with open(self.output_file, 'a') as f:
      publist = []
      pub_from = response.url.split("/")[-1].split(".")[0]
      if pub_from is not '': # Filter out irrelevant information
        for publication in response.css("cite.data"):
          publist.append({
            "title": publication.css("span.title::text").get(),
            "author": publication.css("span a span::text").getall(),
            "from": pub_from,
          })
        f.write("\"%s\": " % pub_from)
        json.dump(publist, f, indent=2)
        f.write(",\n")
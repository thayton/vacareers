#!/usr/bin/env python

import sys
import json
import signal
import urlparse
import requests
import lxml.html

def sigint(signal, frame):
    sys.stderr.write('Exiting...\n')
    sys.exit(0)    

class VaCareersJobScraper(object):
    def __init__(self):
        self.url = 'http://www.vacareers.va.gov/careers/physicians/search-results.asp'
        self.params = {
            'search': 'search',
            'q': '0602',
            'pg': 1
        }

    def scrape_job_links(self):
        jobs = []

        while True:
            r = requests.get(self.url, params=self.params)
            t = lxml.html.fromstring(r.text)
            d = t.cssselect('div#search-results')[0]

            for jdiv in d.cssselect('div.job'):
                job = {}
                job['url'] = urlparse.urljoin(self.url, jdiv.find('a').get('href'))
                job['title'] = jdiv.cssselect('span.job-title')[0].text
                job['location'] = jdiv.cssselect('span.job-location')[0].text
                jobs.append(job)
                break

            # next page
            self.params['pg'] += 1
            print 'page ', self.params['pg']

            x = './/ul[@class="paging-nav"]/a/li[text()="{}"]'
            x = x.format(self.params['pg'])

            try:
                (n,) = t.xpath(x)
            except ValueError: # no more pages
                break

        return jobs

    def scrape_job_description(self, job):
        r = requests.get(job['url'])
        t = lxml.html.fromstring(r.text)
        d = t.cssselect('div.jb-content')
        t = d[0].text_content()
        t = ' '.join(t.split())

        job['description'] = t

    def scrape(self):
        print 'scraping...'
        jobs = self.scrape_job_links()
        for job in jobs:
            self.scrape_job_description(job)

        print json.dumps(jobs, indent=2)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint)
    job_scraper = VaCareersJobScraper()
    job_scraper.scrape()

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
        self.session = requests.Session()

    def scrape_job_links(self):
        jobs = []

        while True:
            sys.stderr.write('scraping page %d\n' % self.params['pg'])

            r = self.session.get(self.url, params=self.params)
            tree = lxml.html.fromstring(r.text)
            rdiv = tree.cssselect('div#search-results')[0]

            for jdiv in rdiv.cssselect('div.job'):
                jdiv_sel_txt = lambda sel: jdiv.cssselect(sel)[0].text
                jdiv_url = lambda: urlparse.urljoin(r.url, jdiv.find('a').get('href'))

                job = {}
                job['url'] = jdiv_url()
                job['title'] = jdiv_sel_txt('span.job-title')
                job['location'] = jdiv_sel_txt('span.job-location')
                jobs.append(job)

            # next page
            self.params['pg'] += 1

            sys.stderr.write('# jobs %d\n' % len(jobs))

            # If no page number link, then we're on the last page
            xp = './/ul[@class="paging-nav"]/a/li[text()="{}"]'
            xp = xp.format(self.params['pg'])

            try:
                (n,) = tree.xpath(xp)
            except ValueError: # no more pages
                break

        return jobs

    def scrape_job_description(self, job):
        sys.stderr.write('scraping %s\n' % job['url'])

        r = self.session.get(job['url'])
        tree = lxml.html.fromstring(r.text)

        div = tree.cssselect('div.jb-content')
        txt = div[0].text_content()
        txt = ' '.join(txt.split())

        job['description'] = txt

    def scrape(self):
        jobs = self.scrape_job_links()
        for job in jobs:
            self.scrape_job_description(job)

        with open('vacareers.json', 'w') as fp:
            json.dump(jobs, fp, indent=2)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint)
    job_scraper = VaCareersJobScraper()
    job_scraper.scrape()

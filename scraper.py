#!/usr/bin/env python

import sys
import json
import signal
import urlparse
import requests
import lxml.html

from functools import partial

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

    @staticmethod
    def lxml_text(etree, CSSSelector):
        elem = etree.cssselect(CSSSelector)
        text = elem[0].text_content()
        text = ' '.join(text.split())
        return text

    @staticmethod
    def lxml_html(etree, CSSSelector):
        elem = etree.cssselect(CSSSelector)
        html = lxml.etree.tostring(elem[0])
        return html

    def scrape_job_links(self):
        jobs = []

        while True:
            sys.stderr.write('scraping page %d\n' % self.params['pg'])

            r = self.session.get(self.url, params=self.params)
            tree = lxml.html.fromstring(r.text)
            rdiv = tree.cssselect('div#search-results')[0]

            for jdiv in rdiv.cssselect('div.job'):
                jdiv_text = lambda sel: self.lxml_text(jdiv, sel)
                jdiv_url = lambda: urlparse.urljoin(r.url, jdiv.find('a').get('href'))

                job = {}
                job['url'] = jdiv_url()
                job['title'] = jdiv_text('span.job-title')
                job['location'] = jdiv_text('span.job-location')
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

        # Bind first argument to 'tree' for all the calls below
        lxml_text = partial(self.lxml_text, tree)
        lxml_html = partial(self.lxml_html, tree)

        job['description'] =        lxml_text('div.jb-content')
        job['contactName'] =        lxml_text('div.jd-sub-header > span > span.contact-item')
        job['contactPhone'] =       lxml_text('div.jd-sub-header > span > span > a > span.contact-item')
        job['contactEmail'] =       lxml_text('div.jd-sub-header > span > a > span.contact-item')
        job['openDate'] =           lxml_text('div.job-details div.left span.detail-detail:nth-of-type(1)')
        job['closeDate'] =          lxml_text('div.job-details div.left span.detail-detail:nth-of-type(2)')
        job['company'] =            lxml_text('div.job-details div.right span.detail-detail:nth-of-type(1)')
        job['seekerRole'] =         lxml_text('div.job-details div.right span.detail-detail:nth-of-type(2)')
        job['type'] =               lxml_text('div.job-details div.right span.detail-detail:nth-of-type(3)')
        job['payrangeFrom'] =       lxml_text('div.estimated-pay div.payrange-left')
        job['payrangeTo'] =         lxml_text('div.estimated-pay div.payrange-right')
        job['aboutVa'] =            lxml_html('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(1) li.accordion-content')
        job['qualifications'] =     lxml_html('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(2) li.accordion-content')
        job['benefits'] =           lxml_html('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(3) li.accordion-content')
        job['howToApply'] =         lxml_html('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(4) li.accordion-content')
        job['additionalDetails'] =  lxml_html('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(5) li.accordion-content')

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

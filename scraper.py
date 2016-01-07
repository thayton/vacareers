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

    @staticmethod
    def lxml_text(etree, CSSSelector):
        elem = etree.cssselect(CSSSelector)
        text = elem[0].text_content()
        return text

    @staticmethod
    def lxml_html(etree, CSSSelector):
        elem = etree.cssselect(CSSSelector)
        html = lxml.etree.tostring(elem[0], pretty_print=True)
        return html

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

        # url:                window.location.href,
        # title:              getContentSafe('div.jb-title'),
        # location:           getContentSafe('div.jb-subtitle'),
        # description:        getHtmlSafe('div.jb-content'),
        # contactName:        getContentSafe('div.jd-sub-header > span > span.contact-item'),
        # contactPhone:       getContentSafe('div.jd-sub-header > span > span > a > span.contact-item'),
        # contactEmail:       getContentSafe('div.jd-sub-header > span > a > span.contact-item'),
        # openDate:           getContentSafe('div.job-details div.left span.detail-detail:nth-of-type(1)'),
        # closeDate:          getContentSafe('div.job-details div.left span.detail-detail:nth-of-type(2)'),
        # company:            getContentSafe('div.job-details div.right span.detail-detail:nth-of-type(1)'),
        # seekerRole:         getContentSafe('div.job-details div.right span.detail-detail:nth-of-type(2)'),
        # type:               getContentSafe('div.job-details div.right span.detail-detail:nth-of-type(3)'),
        # payrangeFrom:       getContentSafe('div.estimated-pay div.payrange-left'),
        # payrangeTo:         getContentSafe('div.estimated-pay div.payrange-right'),
        # aboutVa:            getHtmlSafe('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(1) li.accordion-content'),
        # qualifications:     getHtmlSafe('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(2) li.accordion-content'),
        # benefits:           getHtmlSafe('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(3) li.accordion-content'),
        # howToApply:         getHtmlSafe('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(4) li.accordion-content'),
        # additionalDetails:  getHtmlSafe('.detail-accordions .jb-accordion li.accordion-item:nth-of-type(5) li.accordion-content')

        div = tree.cssselect('div.jb-content')
        txt = div[0].text_content()
        txt = ' '.join(txt.split())

        job['description'] = txt
        job['contactName'] =        self.lxml_text(tree, 'div.jd-sub-header > span > span.contact-item')
        job['contactPhone'] =       self.lxml_text(tree, 'div.jd-sub-header > span > span > a > span.contact-item')
        job['contactEmail'] =       self.lxml_text(tree, 'div.jd-sub-header > span > a > span.contact-item')
        job['openDate'] =           self.lxml_text(tree, 'div.job-details div.left span.detail-detail:nth-of-type(1)')
        job['closeDate'] =          self.lxml_text(tree, 'div.job-details div.left span.detail-detail:nth-of-type(2)')
        job['company'] =            self.lxml_text(tree, 'div.job-details div.right span.detail-detail:nth-of-type(1)')
        job['seekerRole'] =         self.lxml_text(tree, 'div.job-details div.right span.detail-detail:nth-of-type(2)')
        job['type'] =               self.lxml_text(tree, 'div.job-details div.right span.detail-detail:nth-of-type(3)')
        job['payrangeFrom'] =       self.lxml_text(tree, 'div.estimated-pay div.payrange-left')
        job['payrangeTo'] =         self.lxml_text(tree, 'div.estimated-pay div.payrange-right')
        job['aboutVa'] =            self.lxml_html(tree, '.detail-accordions .jb-accordion li.accordion-item:nth-of-type(1) li.accordion-content')
        job['qualifications'] =     self.lxml_html(tree, '.detail-accordions .jb-accordion li.accordion-item:nth-of-type(2) li.accordion-content')
        job['benefits'] =           self.lxml_html(tree, '.detail-accordions .jb-accordion li.accordion-item:nth-of-type(3) li.accordion-content')
        job['howToApply'] =         self.lxml_html(tree, '.detail-accordions .jb-accordion li.accordion-item:nth-of-type(4) li.accordion-content')
        job['additionalDetails'] =  self.lxml_html(tree, '.detail-accordions .jb-accordion li.accordion-item:nth-of-type(5) li.accordion-content')

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

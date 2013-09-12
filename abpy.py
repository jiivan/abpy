import re
import sys
import urlparse


RE_TOK = re.compile('\W')


MAP_RE = (('\|\|','(//|\.)'),
          ('\^', r'[/\\:+!@#\$^\^&\*\(\)\|]'),
          ('\*', r'.*'))

class RuleSyntaxError(Exception):
    pass

TYPE_OPTS = (('script', 'external scripts loaded via HTML script tag'),
             ('image', 'regular images, typically loaded via HTML img tag'),
             ('stylesheet', 'external CSS stylesheet files'),
             ('object', 'content handled by browser plugins, e.g. Flash or Java'),
             ('xmlhttprequest', 'requests started by the XMLHttpRequest object'),
             ('object-subrequest', 'requests started plugins like Flash'),
             ('object_subrequest', 'requests started plugins like Flash (non-standard form used in some lists)'),
             ('subdocument', 'embedded pages, usually included via HTML frames'),
             ('document', 'the page itself (only exception rules can be applied to the page)'),
             ('elemhide', 'for exception rules only, similar to document but only disables element hiding rules on the page rather than all filter rules (Adblock Plus 1.2 and higher required)'),
             ('popup', 'Unsupported option used in some files'),
             ('third-party', 'Restriction to third-party/first-party requests: If the third-party option is specified, the filter is only applied to requests from a different origin than the currently viewed page. Similarly, ~third-party restricts the filter to requests from the same origin as the currently viewed page.'),
             ('collapse', 'this option will override the global "Hide placeholders of blocked elements" option and make sure the filter always hides the element. Similarly the ~collapse option will make sure the filter never hides the element.'),
             ('background', 'The type options background, xbl, ping and dtd are outdated and should no longer be used.'),
             ('xbl', 'The type options background, xbl, ping and dtd are outdated and should no longer be used.'),
             ('dtd', 'The type options background, xbl, ping and dtd are outdated and should no longer be used.'),
             ('media', 'Unknown option rarely used'),
             ('other', 'types of requests not covered in the list above'))
TYPE_OPT_IDS = [x[0] for x in TYPE_OPTS]

# Problematic entries:
# dating.dk#DIV(id^=ctl00)(id$=_layerClock)
# ||adm.fwmrm.net/p/msnbc_live/$object-subrequest,third-party,domain=~msnbc.msn.com,~www.nbcnews.com


class Rule(object):
    def __init__(self, rule_str):
        self.rule_str = rule_str = rule_str.strip()
        if '$' in rule_str:
            try:
                self.pattern, self.optstring = rule_str.split('$')
            except ValueError:
                raise RuleSyntaxError()
        else:
            self.pattern = self.rule_str
            self.optstring = ''
        self.regex = self._to_regex()
        if self.optstring:
            opts = self.optstring.split(',')
        else:
            opts = []
        self.excluded_elements = set()
        self.matched_elements = set()
        self.enabled_domains = set()
        self.disabled_domains = set()
        for o in opts:
            if o.startswith('~') and o[1:] in TYPE_OPT_IDS:
                self.excluded_elements.add(o[1:])
            elif o in TYPE_OPT_IDS:
                self.matched_elements.add(o)
            elif o.startswith('domain='):
                token, domains = o.split('=')
                for domain in domains.split(','):
                    for ored_domain in domain.split('|'):
                        if domain.startswith('~'):
                            self.disabled_domains.add(domain[1:])
                        else:
                            self.enabled_domains.add(domain)
            else:
                #print self.rule_str, self.optstring, repr(o)
                raise RuleSyntaxError()
        if not self.matched_elements:
            self.matched_elements = set(['other'])

    def get_tokens(self):
        return RE_TOK.split(self.pattern)

    def match(self, url, elementtypes=None):
        if elementtypes:
            if self.excluded_elements.intersection(elementtypes):
                return False
            if 'other' not in self.matched_elements:
                if not self.matched_elements.intersection(elementtypes):
                    return False
        if self.enabled_domains or self.disabled_domains:
            hostname = urlparse.urlparse(url).hostname
            if hostname in self.disabled_domains:
                return False
            if self.enabled_domains and not (hostname in self.enabled_domains):
                return False
        return self.regex.search(url)

    def _to_regex(self):
        re_str = re.escape(self.pattern)
        for m in MAP_RE:
            re_str = re_str.replace(*m)
        return re.compile(re_str)
    
    def __unicode__(self):
        return self.rule_str


class Filter(object):
    def __init__(self, f):
        self.index = {}
        for rul in f.xreadlines():
            if rul.startswith('!'): # Comment 
                continue 
            if '##' in rul: # HTML rule
                continue
            try:
                rule = Rule(rul)
            except RuleSyntaxError:
                print 'syntax error in ', rul
            for tok in rule.get_tokens():
                if len(tok) > 2:
                    if tok not in self.index:
                        self.index[tok] = []
                    self.index[tok].append(rule)

    def match(self, url, elementtypes=None):
        tokens = RE_TOK.split(url)
        for tok in tokens:
            if len(tok) > 2:
                if tok in self.index:
                    for rule in self.index[tok]:
                        if rule.match(url, elementtypes=elementtypes):
                            #print unicode(rule)
                            return rule


if __name__ == '__main__':
    f = Filter(file('easylist.txt'))
    print 'start matching'
    f.match(sys.argv[1])

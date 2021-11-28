from lxml import etree
from io import StringIO
import urllib.request
import re
import html
import sys

import os
import json

#A small script to transform a Wikipedia page into a wordpress page.
#The script takes a Wikipedia page using the Wikipedia page API.
#Most of the transformations are trivial and aim at simplifying the wikipedia HTML code.
#The most tricky part are the references:
#the complicated Wikipedia reference system (with harvsp) is replaced by a tooltip, using the tooltip shortcode from the Shortcodes Ultimate extension.

#We retrieve the command line argument.
#In case there isn't any we are simply going to use the Diamond open access page as demonstration
if len(sys.argv)>1:
    article_name = sys.argv[1]
else:
    article_name = "Diamond open access"

#We load the article from the Wikipedia API and get the latest version.
article_name = article_name.replace(" ", "_")

with urllib.request.urlopen("https://en.wikipedia.org/w/api.php?action=parse&page=" + article_name + "&prop=text&formatversion=2&format=json") as url:
    html_wiki = json.loads(url.read().decode())
    html_wiki = html_wiki["parse"]["text"]

#We parse it with lxml
html_content = etree.parse(StringIO(html_wiki)).getroot()

######################
#1. Trivial cleaning.#
######################

#We remove the table of content:
html_body = html_content.xpath("//div[@class='mw-parser-output']")
toc_content = html_content.xpath("//div[@class='toc']")[0]
toc_content.getparent().remove(toc_content)

#We remove the navbox at the ends
navbox_content = html_content.xpath("//div[@class='navbox']")
for navbox_element in navbox_content:
    navbox_element.getparent().remove(navbox_element)

navbox_content = html_content.xpath("//div[@class='navbox-styles']")
for navbox_element in navbox_content:
    navbox_element.getparent().remove(navbox_element)

#We simplify the title:
#H2 titles:
for titles_h2 in html_content.xpath("//h2"):
    new_titles_h2 = etree.fromstring("<h1>" + titles_h2.xpath('string(span[@class="mw-headline"])') + "</h1>")
    titles_h2.getparent().replace(titles_h2, new_titles_h2)

#H3 titles:
for titles_h3 in html_content.xpath("//h3"):
    content_title = titles_h3.xpath('string(span[@class="mw-headline"])')
    content_title = content_title.replace("&", "&amp;")
    new_titles_h3 = etree.fromstring("<h2>" + content_title + "</h2>")
    titles_h3.getparent().replace(titles_h3, new_titles_h3)

################
#2. References.#
################

#This is by far the most complicated parsing.

reference_numbering = 1

#First we extract all the "sup" tags that contain the footnote.
for reference in html_content.xpath("//sup[@class='reference']"):

    #A strange issue: retrieving the sup tags also yields some part of the text that follows.
    #We are careful to keep it.
    text_after_reference = etree.tostring(reference).decode("utf-8")
    text_after_reference = text_after_reference.replace("&", "&amp;")

    text_after_reference = re.sub('<[^<]+?>', '', text_after_reference)
    text_after_reference = re.sub('\[\d+\]', '', text_after_reference)

    #First we retrieve the id of the footnote.
    reference_id = reference.xpath("a")[0].attrib["href"]

    #Then we retrive the id of the reference in the footnote list.
    matching_reference = html_content.xpath("//li[@id='" + reference_id.replace("#", "") + "']")[0]
    reference_text = matching_reference.xpath("span[@class='reference-text']")[0]

    #Check if there is a a in the reference.
    reference_bib_id = reference_text.xpath("a")
    if(len(reference_bib_id)>0):
        reference_bib_id = reference_bib_id[0].attrib["href"]
    else:
        reference_bib_id = ""

    #If there is an associated reference_bib_id from the harvsp notation we look for it in the bibliography.
    if "#CITEREF" in reference_bib_id:
        matching_bibliography = html_content.xpath("//cite[@id='" + reference_bib_id.replace("#", "") + "']")[0]
        reference_text = reference_text.xpath("string(a)")

        #The text that will be outputed in the tooltip (matching bibliography) is striped from all the html.
        matching_bibliography = etree.tostring(matching_bibliography).decode("utf-8")
        matching_bibliography = re.sub(r'^<cite.+?>', '', matching_bibliography)
        matching_bibliography = re.sub(r'</cite>', '', matching_bibliography)
        matching_bibliography = re.sub('<[^<]+?>', '', matching_bibliography)
        matching_bibliography = re.sub('"', '', matching_bibliography)

        #We create the code for the new reference.
        new_reference = '<span> [su_tooltip style="dark" position="north" max_width="500" content="' + matching_bibliography + '"](<a class="reference_synthesis" href="' + reference_bib_id + '">' + reference_text + '</a>)[/su_tooltip] ' + text_after_reference + '</span>'
        new_reference = etree.fromstring(new_reference.replace("&", "&amp;"))
        reference.getparent().replace(reference, new_reference)

    #If that's not the case we are dealing with a simple note.
    else:
        reference_text = etree.tostring(reference_text).decode("utf-8")
        reference_text = reference_text.replace('<span class="reference-text">', '').replace('</span>', '')
        reference_text = re.sub('<[^<]+?>', '', reference_text)
        reference_text = re.sub('"', '', reference_text)
        new_reference = '<span> [su_tooltip style="dark" position="north" max_width="500" content="' + reference_text + '"](<a class="reference_synthesis" href="' + reference_bib_id + '">note n°' + str(reference_numbering) + '</a>)[/su_tooltip] ' + text_after_reference + '</span>'
        new_reference = etree.fromstring(new_reference.replace("&", "&amp;"))
        reference.getparent().replace(reference, new_reference)
        reference_numbering = reference_numbering + 1

############
#3. Images.#
############

#The main issue is that by default Wikipedia only outputs relative links to the image.
#We have to replace them by absolute links to Wikimedia Commons.
#By the way, we clean up a bit and replace the image and caption mediawiki notation by the wordpress notation.
for image in html_content.xpath("//div[@class='thumbinner']"):
    image_ref_html = image.xpath("a")[0]
    image_ref = image_ref_html.attrib["href"].replace("/wiki/File:", "")
    image_ref = "https://commons.wikimedia.org/wiki/Special:FilePath/" + image_ref + "?width=200"
    image_caption = image.xpath("string(div[@class='thumbcaption'])")
    image_new_html = etree.fromstring('<figure class="wp-block-image size-medium"><img class="aligncenter" src="' + image_ref + '"/><figcaption style="text-align: center;">' + image_caption + '</figcaption></figure>')
    image.getparent().replace(image, image_new_html)


#Finally we replace all the special code characters of html by their text equivalent.
html_content_string = etree.tostring(html_content).decode("utf-8")
html_content_string = html.unescape(html_content_string)

open(article_name + ".html", 'w').write(html_content_string)
